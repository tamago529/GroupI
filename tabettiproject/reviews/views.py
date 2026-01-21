from django.shortcuts import render, get_object_or_404
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View


from commons.models import Review, ReviewReport,CustomerAccount, ReviewPhoto,Store, Reservator, Reservation, ReservationStatus
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse
from datetime import date, time
from django.db.models import Max, Count

from django.shortcuts import render, redirect
from django.views.generic import View
from django.urls import reverse
from datetime import date, time
from django.contrib import messages
from django.utils import timezone

from commons.models import (
    CustomerAccount, Store,
    Reservator, Reservation, ReservationStatus,
    StoreInfoReport, StoreInfoReportPhoto
)

from django.shortcuts import render, redirect
from django.views.generic import View
from django.urls import reverse
from django.contrib import messages
from datetime import date, time

from commons.models import (
    CustomerAccount, Store,
    Reservator, Reservation, ReservationStatus,
    Review,
)

class customer_review_listView(LoginRequiredMixin, View):
    template_name = "reviews/customer_review_list.html"

    def _get_login_customer(self, request):
        # CustomerAccount を pk で引き直す（継承モデル対策）
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def _get_store(self, request):
        sid = request.GET.get("store_id") or request.POST.get("store_id")
        if sid:
            store = Store.objects.filter(pk=sid).first()
            if store:
                return store
        return Store.objects.order_by("pk").first()

    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        store = self._get_store(request)

        store_reviews = []
        if store:
            store_reviews = (
                Review.objects
                .select_related("reviewer")
                .filter(store=store)
                .order_by("-posted_at")
            )

        # 保存済み判定（ログインユーザー + 対象店舗）
        is_saved = False
        if store:
            saved_status = ReservationStatus.objects.filter(status="保存済み").first()
            reservator = Reservator.objects.filter(customer_account=customer).first()
            if saved_status and reservator:
                is_saved = Reservation.objects.filter(
                    booking_user=reservator,
                    store=store,
                    booking_status=saved_status,
                ).exists()

        context = {
            "shop": store,
            "customer": customer,
            "store_id": store.pk if store else "",
            "reviews": store_reviews,
            "is_saved": is_saved,  # ✅ 追加
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        customer = self._get_login_customer(request)

        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        store_id = request.POST.get("store_id")
        store = Store.objects.filter(pk=store_id).first() if store_id else self._get_store(request)

        if store is None:
            messages.error(request, "店舗情報が取得できませんでした。")
            return redirect(reverse("reviews:customer_review_list"))

        # -------------------------
        # 1) 保存（ログインユーザーに紐づく）
        # -------------------------
        if action == "save_store":
            saved_status, _ = ReservationStatus.objects.get_or_create(status="保存済み")

            reservator, _ = Reservator.objects.get_or_create(
                customer_account=customer,
                defaults={
                    "full_name": customer.nickname,
                    "full_name_kana": customer.nickname,
                    "email": customer.sub_email,
                    "phone_number": customer.phone_number,
                }
            )

            exists = Reservation.objects.filter(
                booking_user=reservator,
                store=store,
                booking_status=saved_status,
            ).exists()

            if exists:
                messages.info(request, "すでに保存済みです。")
            else:
                Reservation.objects.create(
                    booking_user=reservator,
                    store=store,
                    booking_status=saved_status,
                    visit_date=date.today(),
                    visit_time=time(0, 0),
                    visit_count=1,
                    course="保存",
                )
                messages.success(request, "保存しました。")

            return redirect(f"{reverse('reviews:customer_review_list')}?store_id={store.pk}")

        # -------------------------
        # 2) 口コミ投稿（ログインユーザーに紐づく）
        # -------------------------
        if action == "create_review":
            time_slot = (request.POST.get("time_slot") or "").strip()  # "昼" or "夜"
            score_raw = (request.POST.get("score") or "").strip()
            title = (request.POST.get("title") or "").strip()
            body = (request.POST.get("body") or "").strip()
            agree = request.POST.get("agree")  # "on" or None

            try:
                score = int(score_raw)
            except ValueError:
                score = 0

            if time_slot not in ("昼", "夜"):
                messages.error(request, "時間帯（昼/夜）を選択してください。")
                return redirect(f"{reverse('reviews:customer_review_list')}?store_id={store.pk}")

            if score < 1 or score > 5:
                messages.error(request, "星評価（1〜5）を選択してください。")
                return redirect(f"{reverse('reviews:customer_review_list')}?store_id={store.pk}")

            if not title:
                messages.error(request, "タイトルを入力してください。")
                return redirect(f"{reverse('reviews:customer_review_list')}?store_id={store.pk}")

            if not body:
                messages.error(request, "本文を入力してください。")
                return redirect(f"{reverse('reviews:customer_review_list')}?store_id={store.pk}")

            if not agree:
                messages.error(request, "同意にチェックしてください。")
                return redirect(f"{reverse('reviews:customer_review_list')}?store_id={store.pk}")

            review_text = f"【{time_slot}】{title}\n{body}"

            Review.objects.create(
                reviewer=customer,   # ✅ ログインユーザー
                store=store,
                score=score,
                review_text=review_text,
            )

            messages.success(request, "口コミを投稿しました。")
            return redirect(f"{reverse('reviews:customer_review_list')}?store_id={store.pk}")

        return redirect(f"{reverse('reviews:customer_review_list')}?store_id={store.pk}")



from django.shortcuts import render, redirect
from django.views.generic import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from commons.models import CustomerAccount, Reservator, Reservation, ReservationStatus


class customer_store_preserveView(LoginRequiredMixin, View):
    template_name = "reviews/customer_store_preserve.html"

    def _get_login_customer(self, request):
        # CustomerAccount を pk で引き直す（継承モデル対策）
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)

        # 顧客ログインじゃない場合
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        saved_status = ReservationStatus.objects.filter(status="保存済み").first()
        if saved_status is None:
            return render(request, self.template_name, {"customer": customer, "saved_list": []})

        reservator = Reservator.objects.filter(customer_account=customer).first()
        if reservator is None:
            return render(request, self.template_name, {"customer": customer, "saved_list": []})

        saved_list = (
            Reservation.objects
            .select_related("store", "booking_status", "store__area", "store__scene")
            .filter(booking_user=reservator, booking_status=saved_status)
            .order_by("-created_at")
        )

        context = {
            "customer": customer,
            "saved_list": saved_list,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        customer = self._get_login_customer(request)

        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        # ---- 保存解除 ----
        if action == "remove_store":
            reservation_id = request.POST.get("reservation_id")

            if not reservation_id:
                messages.warning(request, "保存解除に必要な情報が不足しています。")
                return redirect(reverse("reviews:customer_store_preserve"))

            deleted, _ = Reservation.objects.filter(
                id=reservation_id,
                booking_user__customer_account=customer,  # ✅ 本人の保存のみ
                booking_status__status="保存済み",
            ).delete()

            if deleted > 0:
                messages.success(request, "保存解除しました。")
            else:
                messages.warning(request, "対象の保存データが見つかりませんでした。")

            return redirect(reverse("reviews:customer_store_preserve"))

        # 想定外POSTはGETへ
        return redirect(reverse("reviews:customer_store_preserve"))
class customer_reviewer_detailView(LoginRequiredMixin, View):
    template_name = "reviews/customer_reviewer_detail.html"

    def _get_login_customer(self, request):
        # マルチテーブル継承対策：CustomerAccountをpkで引き直す
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)

        # CustomerAccount でログインしてない場合
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        cover_field = getattr(customer, "cover_image", None)
        icon_field = getattr(customer, "icon_image", None)

        context = {
            "customer": customer,
            "user_name": customer.nickname,  # ← ここが表示名
            "cover_image_url": cover_field.url if cover_field else "",
            "user_icon_url": icon_field.url if icon_field else "",

            "stats_reviews": Review.objects.filter(reviewer=customer).count(),
            "stats_photos": ReviewPhoto.objects.filter(review__reviewer=customer).count(),
            "stats_visitors": 0,
            "stats_likes": customer.total_likes,

            "count_reviews": Review.objects.filter(reviewer=customer).count(),
            "count_following": 0,
            "count_followers": 0,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # ✅ hidden の customer_id は使わず、必ずログインユーザー本人を更新
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        # ✅ カバー更新
        if request.FILES.get("cover_image") and hasattr(customer, "cover_image"):
            customer.cover_image = request.FILES["cover_image"]
            customer.save(update_fields=["cover_image"])

        # ✅ アイコン更新
        if request.FILES.get("icon_image") and hasattr(customer, "icon_image"):
            customer.icon_image = request.FILES["icon_image"]
            customer.save(update_fields=["icon_image"])

        return redirect(reverse("reviews:customer_reviewer_detail"))

class customer_reviewer_detail_selfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return redirect(reverse("reviews:customer_reviewer_detail", args=[request.user.pk]))

class customer_reviewer_review_listView(LoginRequiredMixin, View):
    template_name = "reviews/customer_reviewer_review_list.html"

    def _get_login_customer(self, request):
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        cover_field = getattr(customer, "cover_image", None)
        icon_field = getattr(customer, "icon_image", None)

        # ✅ このユーザーの「口コミ（個別）」一覧（削除ボタン用）
        my_reviews = (
            Review.objects
            .select_related("store")
            .filter(reviewer=customer)
            .order_by("-posted_at")
        )

        # ✅ 既存の「口コミ投稿したお店」集計（必要なら残す）
        reviewed_store_rows = (
            Review.objects
            .filter(reviewer=customer)
            .values("store_id", "store__store_name", "store__branch_name")
            .annotate(
                latest_posted_at=Max("posted_at"),
                visit_count=Count("id"),
            )
            .order_by("-latest_posted_at")
        )

        # ✅ 追加モーダル用：店舗プルダウン
        store_choices = Store.objects.order_by("store_name", "branch_name")

        context = {
            "customer": customer,
            "user_name": customer.nickname,
            "cover_image_url": cover_field.url if cover_field else "",
            "user_icon_url": icon_field.url if icon_field else "",

            "reviewed_store_list": reviewed_store_rows,
            "reviewed_total": reviewed_store_rows.count(),

            "my_reviews": my_reviews,
            "my_reviews_total": my_reviews.count(),

            "store_choices": store_choices,  # ✅ 追加
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        action = request.POST.get("action")

        # -------------------------
        # 1) 口コミ追加
        # -------------------------
        if action == "create_review":
            store_id = request.POST.get("store_id")
            store = Store.objects.filter(pk=store_id).first() if store_id else None
            if store is None:
                messages.error(request, "店舗を選択してください。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            time_slot = (request.POST.get("time_slot") or "").strip()  # "昼" or "夜"
            score_raw = (request.POST.get("score") or "").strip()
            title = (request.POST.get("title") or "").strip()
            body = (request.POST.get("body") or "").strip()
            agree = request.POST.get("agree")  # "on" or None

            try:
                score = int(score_raw)
            except ValueError:
                score = 0

            if time_slot not in ("昼", "夜"):
                messages.error(request, "時間帯（昼/夜）を選択してください。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            if score < 1 or score > 5:
                messages.error(request, "星評価（1〜5）を選択してください。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            if not title:
                messages.error(request, "タイトルを入力してください。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            if not body:
                messages.error(request, "本文を入力してください。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            if not agree:
                messages.error(request, "同意にチェックしてください。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            review_text = f"【{time_slot}】{title}\n{body}"

            Review.objects.create(
                reviewer=customer,
                store=store,
                score=score,
                review_text=review_text,
            )

            messages.success(request, "口コミを投稿しました。")
            return redirect(reverse("reviews:customer_reviewer_review_list"))

        # -------------------------
        # 2) 口コミ削除（自分の口コミのみ）
        # -------------------------
        if action == "delete_review":
            review_id = request.POST.get("review_id")
            if not review_id:
                messages.error(request, "削除対象の口コミが取得できませんでした。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            deleted, _ = Review.objects.filter(
                id=review_id,
                reviewer=customer,
            ).delete()

            if deleted == 0:
                messages.error(request, "削除できませんでした（他ユーザーの口コミ、または存在しません）。")
            else:
                messages.success(request, "口コミを削除しました。")

            return redirect(reverse("reviews:customer_reviewer_review_list"))

        return redirect(reverse("reviews:customer_reviewer_review_list"))


class customer_reviewer_searchView(TemplateView):
    template_name = "reviews/customer_reviewer_search.html"

class customer_review_reportView(LoginRequiredMixin, View):
    template_name = "reviews/customer_review_report.html"

    def _get_login_customer(self, request):
        # マルチテーブル継承対策：CustomerAccountをpkで引き直す
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        context = {
            "customer": customer,
            "display_nickname": customer.nickname,
            "display_email": customer.sub_email or customer.email,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "ユーザー情報が取得できませんでした。")
            return redirect(reverse("reviews:customer_review_report"))

        message = (request.POST.get("message") or "").strip()
        user_type = (request.POST.get("user_type") or "").strip()  # 1/2/3
        agree = request.POST.get("agree")  # on/None

        if not message:
            messages.error(request, "お問い合わせ内容をご記入ください。")
            return redirect(reverse("reviews:customer_review_report"))

        if user_type not in ("1", "2", "3"):
            messages.error(request, "ご入力者を選択してください。")
            return redirect(reverse("reviews:customer_review_report"))

        if not agree:
            messages.error(request, "同意事項にチェックしてください。")
            return redirect(reverse("reviews:customer_review_report"))

        user_type_label = {"1": "一般ユーザー", "2": "飲食店関係者", "3": "その他"}.get(user_type, "-")
        now_str = timezone.localtime(timezone.now()).strftime("%Y/%m/%d %H:%M")

        entry = (
            f"【{now_str}】入力者:{user_type_label}\n"
            f"ニックネーム:{customer.nickname}\n"
            f"メール:{(customer.sub_email or customer.email)}\n"
            f"内容:\n{message}\n"
            f"------------------------------\n"
        )

        customer.inquiry_log = entry + (customer.inquiry_log or "")
        customer.save(update_fields=["inquiry_log"])

        return redirect(f"{reverse('reviews:customer_common_complete')}?msg=問い合わせが完了しました。")

class store_review_reportView(TemplateView):
    template_name = "reviews/store_review_report.html"


class store_review_listView(TemplateView):
    template_name = "reviews/store_review_list.html"


class company_review_listView(TemplateView):
    template_name = "reviews/company_review_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ✅ チェックONなら "reported=1" をURLに付ける想定
        only_reported = self.request.GET.get("reported") == "1"

        # ✅ 通報済みID（バッジ表示・JS用）
        reported_review_ids = (
            ReviewReport.objects
            .filter(report_status=True)
            .values_list("review_id", flat=True)
            .distinct()
        )

        # ✅ 一覧（チェック状態で切り替え）
        qs = Review.objects.select_related("reviewer", "store").all()

        if only_reported:
            qs = qs.filter(reviewreport__report_status=True).distinct()

        reviews = qs.order_by("-posted_at")

        context["reviews"] = reviews
        context["reported_review_ids"] = reported_review_ids
        context["only_reported"] = only_reported  # テンプレでchecked制御に使う
        return context
        


# reviews/views.py（既存の customer_report_input を置き換え）

class customer_report_input(LoginRequiredMixin, View):
    template_name = "reviews/customer_report_input.html"

    def _get_login_customer(self, request):
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        # store_id が来ていれば対象店舗を特定（無くてもOKにしておく）
        store_id = request.GET.get("store_id")
        store = Store.objects.filter(pk=store_id).first() if store_id else None

        return render(request, self.template_name, {"customer": customer, "store": store})

    def post(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        message = (request.POST.get("comment") or "").strip()
        agree = request.POST.get("agree")  # on / None
        store_id = request.POST.get("store_id") or ""
        store = Store.objects.filter(pk=store_id).first() if store_id else None

        if not message:
            messages.error(request, "コメントを入力してください。")
            redirect_url = reverse("reviews:customer_report_input")
            if store_id:
                redirect_url += f"?store_id={store_id}"
            return redirect(redirect_url)

        if not agree:
            messages.error(request, "同意事項にチェックしてください。")
            redirect_url = reverse("reviews:customer_report_input")
            if store_id:
                redirect_url += f"?store_id={store_id}"
            return redirect(redirect_url)

        report = StoreInfoReport.objects.create(
            store=store,
            reporter=customer,
            message=message,
        )

        # ファイル（最大5枚）
        files = request.FILES.getlist("files") or request.FILES.getlist("files[]")
        files = files[:5]
        for f in files:
            StoreInfoReportPhoto.objects.create(report=report, image=f)

        return redirect(f"{reverse('reviews:customer_common_complete')}?msg=店舗情報の報告が完了しました。")



class reportView(TemplateView):
    template_name = "reviews/report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reports = (
            ReviewReport.objects
            .select_related("review", "reporter", "review__reviewer")
            .all()
            .order_by("-reported_at")
        )
        context["reports"] = reports
        return context
    

class customer_common_completeView(View):
    template_name = "commons/customer_common_complete.html"

    def get(self, request, *args, **kwargs):
        msg = request.GET.get("msg", "完了しました。")
        return render(request, self.template_name, {"msg": msg})
