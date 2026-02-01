from django.shortcuts import render, redirect, get_object_or_404
import urllib.parse
from django.contrib import messages
from django.contrib.auth import logout, login
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Exists, OuterRef
from django.views.generic import ListView, CreateView, View, TemplateView
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from commons.models import StoreAccount, Account, Scene, Store, StoreAccountRequest, ApplicationStatus, Area, CustomerAccount, StoreAccountRequestLog, AccountType
from .forms import CustomerLoginForm, CustomerRegisterForm, CustomerPasswordResetForm, StorePasswordResetForm
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
            .order_by("-logged_at")
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
    
class company_store_review_permitView(LoginRequiredMixin, View):
    def post(self, request, request_id):
        req = get_object_or_404(StoreAccountRequest, id=request_id)

        status_pending = ApplicationStatus.objects.get(status="申請中")
        status_approved = ApplicationStatus.objects.get(status="承認")

        # 二重承認防止
        if req.request_status_id != status_pending.id:
            messages.info(request, "この申請は既に処理済みです。")
            return redirect("accounts:company_store_review_detail", request_id=req.id)

        with transaction.atomic():
            # 1) 申請ステータス更新
            req.request_status = status_approved
            req.approved_at = timezone.now()
            req.save(update_fields=["request_status", "approved_at"])

            # 2) StoreAccount 作成（既存なら取得）
            sa = StoreAccount.objects.filter(store=req.target_store).select_related("store").first()
            if not sa:
                store_type = AccountType.objects.get_or_create(account_type="店舗")[0]

                # username かぶり対策（最低限）
                base_username = f"store_{req.target_store_id}"
                username = base_username
                i = 1
                while StoreAccount.objects.filter(username=username).exists():
                    i += 1
                    username = f"{base_username}_{i}"

                sa = StoreAccount.objects.create(
                    username=username,
                    email=req.email,          # 店舗メール（申請時に Store.email をコピーしてる前提）
                    account_type=store_type,
                    store=req.target_store,
                    admin_email=req.admin_email if hasattr(req, "admin_email") and req.admin_email else req.email,
                    permission_flag=True,
                    is_active=True,
                )
                # 初回はパスワード未設定にしておく
                sa.set_unusable_password()
                sa.save(update_fields=["password"])

            # 3) ✅ 即パスワード再設定メール送信（Django標準）
            form = StorePasswordResetForm(data={"email": sa.email})
            if form.is_valid():
                form.save(
                    request=request,
                    use_https=False,  # 本番は True 推奨（HTTPS環境なら）
                    from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
                    subject_template_name="accounts/password_reset_subject.txt",
                    email_template_name="accounts/store_password_reset_email.html",
                    extra_email_context={
                        "store_name": req.store_name,
                        "branch_name": req.branch_name,
                    },
                )
            else:
                # ここに来るのは基本「メール空」などの異常系
                messages.warning(request, "承認は完了しましたが、再設定メールの送信に失敗しました。")

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

        # CustomerAccount 判定（isinstance ではなくDB存在で判定）
        try:
            customer = CustomerAccount.objects.get(pk=request.user.pk)
        except CustomerAccount.DoesNotExist:
            return redirect("accounts:customer_top")

        store_id = request.POST.get("store_id")
        if not store_id:
            return redirect("accounts:store_account_search")

        store = get_object_or_404(Store, id=store_id)

        # 登録済みは申請不可
        if StoreAccount.objects.filter(store=store).exists():
            return redirect("accounts:store_account_search")

        applicant_name = (request.POST.get("applicant_name") or "").strip()
        relation = (request.POST.get("relation_to_store") or "").strip()
        license_image = request.FILES.get("license_image")

        if not applicant_name or not relation or not license_image:
            return redirect("accounts:store_account_search")

        status_obj = ApplicationStatus.objects.get(status="申請中")

        # 店舗単位で申請中は1つにする（テンプレの「申請中」と整合）
        if StoreAccountRequest.objects.filter(
            target_store=store,
            request_status=status_obj,
        ).exists():
            return redirect("accounts:store_account_search")

        StoreAccountRequest.objects.create(
            requester=customer,
            target_store=store,
            license_image=license_image,
            request_status=status_obj,

            store_name=store.store_name,
            branch_name=store.branch_name,
            email=store.email,
            phone_number=store.phone_number,
            address=store.address,

            applicant_name=applicant_name,
            relation_to_store=relation,
        )
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

        SCENE_IMAGE_MAP = {
            "お一人様": "images/scene_solo.jpg",
            "家族・こどもと": "images/scene_family.jpg",
            "接待": "images/scene_business.jpg",
            "デート": "images/scene_date.jpg",
            "女子会": "images/scene_girls.jpg",
            "合コン": "images/scene_gokon.jpg",
        }

        scenes = list(Scene.objects.all().order_by("id"))
        for s in scenes:
            s.image_static = SCENE_IMAGE_MAP.get(s.scene_name, "images/scene_default.jpg")

        context["scenes"] = scenes
        return context