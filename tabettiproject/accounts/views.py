from django.shortcuts import render, redirect, get_object_or_404
import urllib.parse
from django.contrib import messages
from django.contrib.auth import logout, login
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Exists, OuterRef
from django.views.generic import ListView, CreateView, View, TemplateView
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from commons.models import StoreAccount, Account, Scene, Store, StoreAccountRequest, ApplicationStatus, Area, CustomerAccount, StoreAccountRequestLog, AccountType
from .forms import CustomerLoginForm, CustomerRegisterForm, CustomerPasswordResetForm, StorePasswordResetForm, StoreLoginForm
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,

)
from django.conf import settings

# =========================
# 企業側
# =========================

class CompanyOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    """ログイン必須、かつ「企業」アカウントのみ許可する門番"""
    login_url = 'accounts:company_login' # ログインしてない時の飛ばし先

    def test_func(self):
        # ログインしていて、かつ種類が「企業」なら合格（True）
        user = self.request.user
        return user.is_authenticated and user.account_type.account_type == "企業"

class company_account_managementView(CompanyOnlyMixin, ListView):
    template_name = "accounts/company_account_management.html"
    model = Account
    context_object_name = "accounts"

    def get_queryset(self):
        queryset = super().get_queryset().select_related("account_type")

        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(username__icontains=q) |
                Q(email__icontains=q) |
                Q(customeraccount__nickname__icontains=q)
            )

        selected_type = self.request.GET.get("type", "all")
        if selected_type == "customer":
            queryset = queryset.filter(account_type__account_type="顧客")
        elif selected_type == "store":
            queryset = queryset.filter(account_type__account_type="店舗")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        context["selected_type"] = self.request.GET.get("type", "all")
        return context
def account_delete_execute(request, pk):
    # 削除対象のアカウントを取得
    user = get_object_or_404(Account, pk=pk)
    username = user.username
    
    # データベースから削除（※注意：紐づくデータがある場合、前述のProtectedErrorが出る可能性があります）
    user.delete()
    
    # 完了画面へリダイレクト
    msg = f"アカウント「{username}」の削除"
    return redirect(reverse('commons:company_common_complete') + f"?msg={urllib.parse.quote(msg)}")

class company_loginView(LoginView):
    template_name = "accounts/company_login.html"

    def get_success_url(self):
        return reverse_lazy("accounts:company_top")

    def form_valid(self, form):
        user = form.get_user()
        if user.account_type.account_type != "企業":
            messages.error(self.request, "運用管理アカウント以外はログインできません。")
            return self.form_invalid(form)
        return super().form_valid(form)


def company_logout_view(request):
    logout(request)
    return render(request, "accounts/company_logout.html")


class company_store_review_detailView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/company_store_review_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request_id = self.kwargs["request_id"]

        req = get_object_or_404(StoreAccountRequest, id=request_id)

        log = (
            StoreAccountRequestLog.objects
            .filter(request=req)
            .select_related("request_status")
            .order_by("-updated_at")
        )
        ctx["req"] = req
        ctx["logs"] = log
        return ctx

class company_store_reviewView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/company_store_review.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pending = ApplicationStatus.objects.get(status="申請中")
        
        requests = (
            StoreAccountRequest.objects 
            .filter(request_status=pending)
            .order_by("-requested_at")
        )

        ctx["requests"] = requests
        return ctx
    
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View

from commons.models import AccountType, ApplicationStatus, StoreAccount, StoreAccountRequest

# from .forms import StorePasswordResetForm


class company_store_review_permitView(LoginRequiredMixin, View):
    def post(self, request, request_id):
        req = get_object_or_404(StoreAccountRequest, id=request_id)

        status_pending = ApplicationStatus.objects.get(status="申請中")
        status_approved = ApplicationStatus.objects.get(status="承認")
        status_rejected = ApplicationStatus.objects.get(status="却下")

        # 却下は承認操作不可
        if req.request_status_id == status_rejected.id:
            messages.error(request, "却下済みの申請は承認できません。")
            return redirect("accounts:company_store_review_detail", request_id=req.id)

        # admin_email 必須
        login_email = (getattr(req, "admin_email", "") or "").strip()
        if not login_email:
            messages.error(request, "処理できません：申請に管理者メールアドレス（ログイン用）が登録されていません。")
            return redirect("accounts:company_store_review_detail", request_id=req.id)

        with transaction.atomic():
            # 1) 申請中なら承認にする（承認済みならそのまま）
            send_reset_mail = False
            if req.request_status_id == status_pending.id:
                req.request_status = status_approved
                req.approved_at = timezone.now()
                req.save(update_fields=["request_status", "approved_at"])
                send_reset_mail = True

            # 2) StoreAccount 作成 or 更新
            store_type = AccountType.objects.get_or_create(account_type="店舗")[0]
            sa = StoreAccount.objects.filter(store=req.target_store).select_related("store").first()

            if sa:
                # email unique 衝突チェック（自分以外）
                if StoreAccount.objects.filter(email__iexact=login_email).exclude(pk=sa.pk).exists():
                    messages.error(request, "この管理者メールアドレスは既に別の店舗アカウントで使用されています。")
                    return redirect("accounts:company_store_review_detail", request_id=req.id)

                sa.email = login_email
                sa.admin_email = login_email
                sa.account_type = store_type
                sa.permission_flag = True
                sa.is_active = True
                sa.save(update_fields=["email", "admin_email", "account_type", "permission_flag", "is_active"])
            else:
                # username衝突回避
                base_username = f"store_{req.target_store_id}"
                username = base_username
                i = 1
                while StoreAccount.objects.filter(username=username).exists():
                    i += 1
                    username = f"{base_username}_{i}"

                if StoreAccount.objects.filter(email__iexact=login_email).exists():
                    messages.error(request, "この管理者メールアドレスは既に使用されています。")
                    return redirect("accounts:company_store_review_detail", request_id=req.id)

                sa = StoreAccount.objects.create(
                    username=username,
                    email=login_email,
                    account_type=store_type,
                    store=req.target_store,
                    admin_email=login_email,
                    permission_flag=True,
                    is_active=True,
                )
                sa.set_unusable_password()
                sa.save(update_fields=["password"])
                send_reset_mail = True  # 新規作成なら送る

            # 3) パスワード再設定メール（申請中→承認 or 新規作成時のみ送る）
            if send_reset_mail:
                form = StorePasswordResetForm(data={"email": sa.email})
                if form.is_valid():
                    form.save(
                        request=request,
                        use_https=False,
                        from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
                        subject_template_name="accounts/password_reset_subject.txt",
                        email_template_name="accounts/store_password_reset_email.html",
                        extra_email_context={
                            "store_name": req.store_name,
                            "branch_name": req.branch_name,
                        },
                    )
                else:
                    messages.warning(request, "承認は完了しましたが、再設定メールの送信に失敗しました。")

        # 表示メッセージ
        if req.request_status_id == status_approved.id:
            messages.success(request, "店舗アカウント情報を更新しました。")
        else:
            messages.success(request, "承認しました。店舗へパスワード再設定メールを送信しました。")

        return redirect("accounts:company_store_review_detail", request_id=req.id)

    

class company_store_review_rejectView(LoginRequiredMixin, View):
    def post(self, request, request_id):
        req = get_object_or_404(StoreAccountRequest, id=request_id)

        pending = ApplicationStatus.objects.get(status="申請中")
        rejected = ApplicationStatus.objects.get(status="却下")

        # 二重実行防止
        if req.request_status_id != pending.id:
            return redirect("accounts:company_store_review_detail", request_id=req.id)

        # 将来的に request.POST.get("reject_reason") を使う
        reason = (request.POST.get("reject_reason") or "").strip()
        if not reason:
            reason = "却下"

        with transaction.atomic():
            req.request_status = rejected
            req.save(update_fields=["request_status"])

            StoreAccountRequestLog.objects.create(
                request=req,
                request_status=rejected,
                comment=reason,
            )

        messages.success(request, "却下しました。")
        return redirect("accounts:company_store_review_detail", request_id=req.id)

    def get(self, request, request_id):
        return redirect("accounts:company_store_review_detail", request_id=request_id)


class company_topView(CompanyOnlyMixin, TemplateView):
    template_name = "accounts/company_top.html"




# =========================
# 顧客側
# =========================
class customer_loginView(LoginView):
    template_name = "accounts/customer_login.html"
    authentication_form = CustomerLoginForm

    def get_success_url(self):
        return reverse_lazy("accounts:customer_top")

    def form_valid(self, form):
        user = form.get_user()
        try:
            _ = user.customeraccount
        except Exception:
            messages.error(self.request, "顧客アカウントではありません。")
            return self.form_invalid(form)
        return super().form_valid(form)


# --- 顧客ログアウト ---
def customer_logout_view(request):
    """
    ヘッダーのログアウトリンク（GET）から来ても、
    ログアウト後に customer_logout.html を表示する。
    """
    logout(request)
    return render(request, "accounts/customer_logout.html")


class customer_registerView(CreateView):
    template_name = "accounts/customer_register.html"
    form_class = CustomerRegisterForm
    success_url = reverse_lazy("accounts:customer_top")

    def form_valid(self, form):
        # フォームの保存（ユーザー作成）
        response = super().form_valid(form)
        # 作成したユーザーでログイン
        user = self.object
        login(self.request, user)
        return response


class customer_settingsView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/customer_settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ログインユーザーが CustomerAccount であることを確認
        if 'form' not in context:
            try:
                customer = self.request.user.customeraccount
                from .forms import CustomerSettingsForm
                context['form'] = CustomerSettingsForm(instance=customer)
            except Exception:
                pass
        return context

    def post(self, request, *args, **kwargs):
        try:
            customer = self.request.user.customeraccount
            from .forms import CustomerSettingsForm
            form = CustomerSettingsForm(request.POST, request.FILES, instance=customer)
            if form.is_valid():
                form.save()
                messages.success(request, "設定を変更しました。")
                return redirect("accounts:customer_setting")
            else:
                messages.error(request, "入力内容に不備があります。確認してください。")
                return self.render_to_response(self.get_context_data(form=form))
        except Exception as e:
            messages.error(request, f"エラーが発生しました: {e}")
            return redirect("accounts:customer_setting")


class customermail_sendView(PasswordResetView):
    template_name = "accounts/customer_mail_send.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:customer_password_done")
    from_email = settings.DEFAULT_FROM_EMAIL
    form_class = CustomerPasswordResetForm

    def dispatch(self, request, *args, **kwargs):
        self.from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        return super().dispatch(request, *args, **kwargs)

class customer_password_reset_completeView(PasswordResetCompleteView):
    template_name = "accounts/customer_password_reset_complete.html"
    success_url = reverse_lazy("accounts:customer_password_reset_complete")


class customer_password_doneView(PasswordResetDoneView):
    template_name = "accounts/customer_mail_sent_info.html"


class customer_password_reset_expireView(TemplateView):
    template_name = "accounts/customer_password_reset_expire.html"


class customer_password_resetView(PasswordResetConfirmView):
    template_name = "accounts/customer_password_reset.html"
    success_url = reverse_lazy("accounts:customer_password_reset_complete")


# =========================
# 店舗側
# =========================
class store_account_editView(TemplateView):
    template_name = "accounts/store_account_edit.html"


def is_store_user(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    try:
        _ = user.storeaccount
        return True
    except StoreAccount.DoesNotExist:
        return False
    except Exception:
        return False


class store_loginView(LoginView):
    template_name = "accounts/store_login.html"
    authentication_form = StoreLoginForm

    def get_success_url(self):
        return reverse_lazy("stores:store_top")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not is_store_user(request.user):
            logout(request)
        if is_store_user(request.user):
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        if not is_store_user(user):
            messages.error(self.request, "店舗アカウントではありません。店舗用のログインIDをご確認ください。")
            return self.form_invalid(form)

        remember = self.request.POST.get("remember")
        if not remember:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(None)

        return super().form_valid(form)


# --- 店舗ログアウト（顧客側と同じロジック） ---
def store_logout_view(request):
    """
    ログアウト後に store_logout.html を表示する（顧客側と同じ）
    """
    logout(request)
    return render(request, "accounts/store_logout.html")



class store_registerView(TemplateView):
    template_name = "accounts/store_register.html"


class store_account_application_confirmView(TemplateView):
    template_name = "accounts/store_account_application_confirm.html"


class store_account_application_inputView(TemplateView):
    template_name = "accounts/store_account_application_input.html"


class store_account_application_messageView(TemplateView):
    template_name = "accounts/store_account_application_message.html"


class store_account_mail_sentView(TemplateView):
    template_name = "accounts/store_account_mail_sent.html"


class store_account_privacyView(TemplateView):
    template_name = "accounts/store_account_privacy.html"


class store_account_searchView(TemplateView):
    template_name = "accounts/store_account_search.html"
    paginate_by = 20

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        q_rst_name = (self.request.GET.get("rst_name") or "").strip()
        q_tel = (self.request.GET.get("tel_number") or "").strip()
        q_area = (self.request.GET.get("area") or "").strip()
        page = self.request.GET.get("page") or 1

        pending_status = ApplicationStatus.objects.get(status="申請中")
        rejected_status = ApplicationStatus.objects.get(status="却下")

        # ★ requester を必ず入れる（自分の申請だけ）
        me = self.request.user

        qs = (
            Store.objects.all()
            .select_related("area")
            .annotate(
                has_store_account=Exists(
                    StoreAccount.objects.filter(store_id=OuterRef("pk"))
                ),
                has_pending_request=Exists(
                    StoreAccountRequest.objects.filter(
                        target_store_id=OuterRef("pk"),
                        request_status=pending_status,
                        requester=me,
                    )
                ),
                has_rejected_request=Exists(
                    StoreAccountRequest.objects.filter(
                        target_store_id=OuterRef("pk"),
                        request_status=rejected_status,
                        requester=me,
                    )
                ),
            )
            .order_by("id")
        )

        if q_rst_name:
            qs = qs.filter(Q(store_name__icontains=q_rst_name) | Q(branch_name__icontains=q_rst_name))
        if q_tel:
            qs = qs.filter(phone_number__icontains=q_tel)
        if q_area:
            qs = qs.filter(area_id=q_area)

        total_count = qs.count()
        stores_page = Paginator(qs, self.paginate_by).get_page(page)

        ctx["areas"] = Area.objects.all().order_by("id")
        ctx.update({
            "stores": stores_page,
            "total_count": total_count,
            "q_rst_name": q_rst_name,
            "q_tel": q_tel,
            "q_area": q_area,
        })
        return ctx


class store_account_request_createView(LoginRequiredMixin, View):
    def post(self, request):
        print("### store_account_request_createView POST ###")
        print("POST:", dict(request.POST))
        print("FILES:", request.FILES)

        # ✅ CustomerAccount 実体を取る（多テーブル継承対策）
        try:
            customer = request.user.customeraccount
        except Exception:
            messages.error(request, "顧客ログインが必要です。")
            return redirect("accounts:customer_top")

        store_id = request.POST.get("store_id")
        store = get_object_or_404(Store, id=store_id)

        # 既に店舗アカウントが紐づいている店舗は申請不可
        if StoreAccount.objects.filter(store=store).exists():
            messages.info(request, "この店舗は既に店舗アカウントが登録済みです。")
            return redirect("accounts:store_account_search")

        applicant_name = (request.POST.get("applicant_name") or "").strip()
        relation = (request.POST.get("relation_to_store") or "").strip()
        admin_email = (request.POST.get("admin_email") or "").strip()
        license_image = request.FILES.get("license_image")

        if not applicant_name or not relation or not admin_email or not license_image:
            messages.error(request, "必須項目が不足しています。")
            return redirect("accounts:store_account_search")

        # admin_email 形式チェック（軽く）
        try:
            validate_email(admin_email)
        except ValidationError:
            messages.error(request, "管理者メールアドレスの形式が正しくありません。")
            return redirect("accounts:store_account_search")

        status_pending = ApplicationStatus.objects.get(status="申請中")

        # ✅ 同一店舗に「申請中」が既にあるなら弾く（申請者が違っても）
        if StoreAccountRequest.objects.filter(
            target_store=store,
            request_status=status_pending,
        ).exists():
            messages.info(request, "この店舗は現在申請中です。")
            return redirect("accounts:store_account_search")

        StoreAccountRequest.objects.create(
            requester=customer,            # ✅ CustomerAccount を渡す
            target_store=store,
            license_image=license_image,
            request_status=status_pending,

            store_name=store.store_name,
            branch_name=store.branch_name,
            email=store.email,             # 店舗メール（店舗情報）
            phone_number=store.phone_number,
            address=store.address,

            applicant_name=applicant_name,
            relation_to_store=relation,

            admin_email=admin_email,       # ✅ ログイン用メール
        )

        messages.success(request, "申請を受け付けました。審査結果をお待ちください。")
        return redirect("accounts:store_account_search")
    
class storemail_sendView(PasswordResetView):
    template_name = "accounts/store_mail_send.html"
    email_template_name = "accounts/store_password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:store_password_done")
    from_email = settings.DEFAULT_FROM_EMAIL
    form_class = StorePasswordResetForm

    def dispatch(self, request, *args, **kwargs):
        self.from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        return super().dispatch(request, *args, **kwargs)

class store_password_reset_confirmView(PasswordResetConfirmView):
    template_name = "accounts/store_password_reset_confirm.html"
    success_url = reverse_lazy("accounts:store_password_reset_complete")


class store_password_reset_completeView(PasswordResetCompleteView):
    template_name = "accounts/store_password_reset_complete.html"

class store_account_staff_confirmView(TemplateView):
    template_name = "accounts/store_account_staff_confirm.html"

class store_password_reset_confirmView(PasswordResetConfirmView):
    template_name = "accounts/store_password_reset_confirm.html"
    success_url = reverse_lazy("accounts:store_password_reset_complete")

class store_password_reset_completeView(PasswordResetCompleteView):
    template_name = "accounts/store_password_reset_complete.html"


class store_account_staff_inputView(TemplateView):
    template_name = "accounts/store_account_staff_input.html"


class customer_topView(TemplateView):
    template_name = "accounts/customer_top.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 0) エリア情報の取得（主要エリアとその他）
        all_areas = Area.objects.all().order_by("id")
        
        # 主要エリア定義 (DBの area_name と一致させる)
        major_names = ["東京都", "神奈川県", "愛知県", "大阪府", "京都府", "福岡県"]
        # 画像マッピング (static/images/...)
        major_images = {
            "東京都": "images/area_tokyo.png",
            "神奈川県": "images/area_kanagawa.png",
            "愛知県": "images/area_aichi.png",
            "大阪府": "images/area_osaka.png",
            "京都府": "images/area_kyoto.png",
            "福岡県": "images/area_fukuoka_fix.jpg",
        }

        major_areas = []
        other_areas = []

        for area in all_areas:
            if area.area_name in major_names:
                # 画像属性を一時的に付与
                area.image_static = major_images.get(area.area_name, "images/no_image.png")
                major_areas.append(area)
            else:
                other_areas.append(area)

        # 順番を固定したい場合 (major_names順に並べ替え)
        major_areas.sort(key=lambda x: major_names.index(x.area_name) if x.area_name in major_names else 999)

        context["major_areas"] = major_areas
        context["other_areas"] = other_areas
        context["areas"] = all_areas # 全件も一応残す

        # 1) シーン画像の定義
        SCENE_IMAGE_MAP = {
            "お一人様": "images/scene_solo.jpg",
            "家族・こどもと": "images/scene_family.jpg",
            "接待": "images/scene_business.jpg",
            "デート": "images/scene_date.jpg",
            "女子会": "images/scene_girls.jpg",
            "合コン": "images/scene_gokon.jpg",
        }

        # 2) シーン情報の取得
        scenes = list(Scene.objects.all().order_by("id"))
        for s in scenes:
            s.image_static = SCENE_IMAGE_MAP.get(s.scene_name, "images/scene_default.jpg")

        context["scenes"] = scenes

        # 3) 人気ランキング（weighted_avg_rating で上位5件）
        #    search/views.py と同様の計算式: 
        #    Sum(score * trust) / Sum(trust)
        
        from django.db.models import Avg, Count, Sum, F, ExpressionWrapper, FloatField

        ranking_stores = Store.objects.prefetch_related("images").annotate(
            weighted_avg_rating=Sum(
                F('review__score') * F('review__reviewer__trust_score'),
                output_field=FloatField()
            ) / Sum(F('review__reviewer__trust_score'), output_field=FloatField()),
            review_count_val=Count('review'),
        ).order_by('-weighted_avg_rating', 'id')[:5]

        # テンプレートで星を表示するためのヘルパー
        for store in ranking_stores:
             # None の場合は 0 または 3.0 (表示上のデフォルト)
            rating = store.weighted_avg_rating if store.weighted_avg_rating else 0.0
            store.avg_rating_val = rating
            
            # 星の生成（半星対応）
            full_stars = int(rating)
            half = (rating - full_stars) >= 0.5
            states = []
            for i in range(5):
                if i < full_stars:
                    states.append("full")
                elif i == full_stars and half:
                    states.append("half")
                else:
                    states.append("empty")
            store.star_states = states

        context["ranking_stores"] = ranking_stores

        # 4) 星の合計獲得数ランキング（総スコアで上位5件）
        total_star_stores = Store.objects.prefetch_related("images").annotate(
            total_score_val=Sum(
                F('review__score'),
                output_field=FloatField()
            )
        ).order_by('-total_score_val', 'id')[:5]

        # ヘルパー（合計ランキング用）
        for store in total_star_stores:
             # display rating (avg)
             # 別途 avg_rating 計算しないと avg が出せないのでここで計算 or annotate する
             # ここでは簡易的に aggregate せず review__score の平均を出すアノテート入れてもいいが、
             # 既存 ranking_stores と被らないようにもう一度記述するか、共通化するか。
             # シンプルに annotate で avg も取る。
             pass

        # 上記で annotate してないので、改めて取る（チェーンできるが可読性重視で書き直し）
        # 実際には total_score_val だけで並び替え済み。
        # 4) 星の合計獲得数ランキング（総スコアで上位5件）
        total_star_stores = Store.objects.prefetch_related("images").annotate(
             total_score_val=Sum('review__score'),
             avg_rating_val=Avg('review__score')
        ).order_by('-total_score_val', 'id')[:5]

        for store in total_star_stores:
            rating = store.avg_rating_val if store.avg_rating_val else 0.0
            full_stars = int(rating)
            half = (rating - full_stars) >= 0.5
            states = []
            for i in range(5):
                if i < full_stars:
                    states.append("full")
                elif i == full_stars and half:
                    states.append("half")
                else:
                    states.append("empty")
            store.star_states = states

        context["total_star_stores"] = total_star_stores

        # 5) 口コミから探す（ランダム4件）
        from commons.models import Review
        # order_by('?') は大量データだと遅いが、小規模ならOK
        pickup_reviews = (
            Review.objects
            .select_related("reviewer", "store", "store__area")
            .prefetch_related("photos")
            .order_by("?")[:4]
        )
        # 評価ヘルパー処理（スター表示用）
        for r in pickup_reviews:
            r.avg_rating_val = float(r.score) # Reviewモデルは score (int) だが float扱いにしておく
            full_stars = int(r.avg_rating_val)
            half = (r.avg_rating_val - full_stars) >= 0.5
            states = []
            for i in range(5):
                if i < full_stars:
                    states.append("full")
                elif i == full_stars and half:
                    states.append("half")
                else:
                    states.append("empty")
            r.star_states = states

        context["pickup_reviews"] = pickup_reviews

        # 6) ユーザーを探す（ランダム6件）
        from commons.models import CustomerAccount, Follow
        random_users = CustomerAccount.objects.all().order_by("?")
        if self.request.user.is_authenticated:
            random_users = random_users.exclude(pk=self.request.user.pk)
        
        random_users = random_users[:6]
        
        pickup_users = []
        viewer = None
        if self.request.user.is_authenticated:
            viewer = CustomerAccount.objects.filter(pk=self.request.user.pk).first()

        for u in random_users:
            is_following = False
            if viewer:
                is_following = Follow.objects.filter(follower=viewer, followee=u).exists()
            
            pickup_users.append({
                "account": u,
                "is_following": is_following,
            })
        context["pickup_users"] = pickup_users

        return context