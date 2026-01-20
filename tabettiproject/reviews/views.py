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

from django.shortcuts import render, redirect
from django.views.generic import View
from django.urls import reverse
from datetime import date, time
from django.contrib import messages

from commons.models import (
    CustomerAccount, Store,
    Reservator, Reservation, ReservationStatus,
)

class customer_review_listView(View):
    template_name = "reviews/customer_review_list.html"

    def _get_customer(self, request):
        """
        ログイン未実装前提：
        - ?customer_id=xx / POST customer_id があれば優先
        - なければ CustomerAccount 先頭1件
        """
        cid = request.GET.get("customer_id") or request.POST.get("customer_id")
        if cid:
            customer = CustomerAccount.objects.filter(pk=cid).first()
            if customer:
                return customer
        return CustomerAccount.objects.order_by("pk").first()

    def _get_store(self, request):
        """
        - ?store_id=xx / POST store_id があれば優先
        - なければ Store 先頭1件
        """
        sid = request.GET.get("store_id") or request.POST.get("store_id")
        if sid:
            store = Store.objects.filter(pk=sid).first()
            if store:
                return store
        return Store.objects.order_by("pk").first()

    def get(self, request, *args, **kwargs):
        customer = self._get_customer(request)
        store = self._get_store(request)

        # 店舗が1件もない場合でも落とさない
        context = {
            "shop": store,  # テンプレが shop を見てるのでそのまま
            "customer": customer,
            "customer_id": customer.pk if customer else "",
            "store_id": store.pk if store else "",
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # 保存ボタン以外のPOSTは無視してGETに戻す
        action = request.POST.get("action")
        if action != "save_store":
            return redirect(reverse("reviews:customer_review_list"))

        customer = self._get_customer(request)

        # 保存先のstoreは「POSTのstore_id」を最優先にする（押した店を確実に保存）
        store_id = request.POST.get("store_id")
        store = Store.objects.filter(pk=store_id).first() if store_id else self._get_store(request)

        if customer is None or store is None:
            return redirect(reverse("reviews:customer_review_list"))

        # 予約ステータス「保存済み」を用意
        saved_status, _ = ReservationStatus.objects.get_or_create(status="保存済み")

        # Reservator を（顧客に紐づく形で）用意
        reservator, _ = Reservator.objects.get_or_create(
            customer_account=customer,
            defaults={
                "full_name": customer.nickname,
                "full_name_kana": customer.nickname,   # 仮
                "email": customer.sub_email,
                "phone_number": customer.phone_number,
            }
        )

        # すでに保存済みなら重複作成しない
        exists = Reservation.objects.filter(
            booking_user=reservator,
            store=store,
            booking_status=saved_status,
        ).exists()

        if not exists:
            Reservation.objects.create(
                booking_user=reservator,
                store=store,
                booking_status=saved_status,
                visit_date=date.today(),           # 保存用ダミー
                visit_time=time(0, 0),             # 保存用ダミー
                visit_count=1,                     # 保存用ダミー
                course="保存",                     # 保存用ダミー
            )

        # 保存リストへ（customer_id を引き継ぐ）
        return redirect(
            f"{reverse('reviews:customer_store_preserve')}?customer_id={customer.pk}"
        )


class customer_store_preserveView(View):
    template_name = "reviews/customer_store_preserve.html"

    def _get_customer(self, request):
        """
        - GET ?customer_id=xx を優先
        - POST customer_id=xx も見る（保存解除POSTのため）
        - なければ CustomerAccount 先頭1件
        """
        cid = request.GET.get("customer_id") or request.POST.get("customer_id")
        if cid:
            customer = CustomerAccount.objects.filter(pk=cid).first()
            if customer:
                return customer
        return CustomerAccount.objects.order_by("pk").first()

    def post(self, request, *args, **kwargs):
        """
        保存解除（Reservationの「保存済み」を削除）
        """
        action = request.POST.get("action")
        if action != "remove_store":
            # 想定外POSTは一覧へ戻す
            customer = self._get_customer(request)
            cid = customer.pk if customer else ""
            return redirect(f"{reverse('reviews:customer_store_preserve')}?customer_id={cid}")

        customer = self._get_customer(request)
        if customer is None:
            return redirect(reverse("reviews:customer_store_preserve"))

        saved_status = ReservationStatus.objects.filter(status="保存済み").first()
        reservator = Reservator.objects.filter(customer_account=customer).first()
        if saved_status is None or reservator is None:
            return redirect(f"{reverse('reviews:customer_store_preserve')}?customer_id={customer.pk}")

        # 解除対象（reservation_id を優先）
        reservation_id = request.POST.get("reservation_id")
        store_id = request.POST.get("store_id")

        qs = Reservation.objects.filter(
            booking_user=reservator,
            booking_status=saved_status,
        )

        if reservation_id:
            qs = qs.filter(pk=reservation_id)
        elif store_id:
            qs = qs.filter(store_id=store_id)
        else:
            # 解除対象が取れないなら何もしない
            return redirect(f"{reverse('reviews:customer_store_preserve')}?customer_id={customer.pk}")

        qs.delete()

        return redirect(f"{reverse('reviews:customer_store_preserve')}?customer_id={customer.pk}")

    def get(self, request, *args, **kwargs):
        customer = self._get_customer(request)

        # 顧客がいない場合でも落とさない
        if customer is None:
            context = {"customer": None, "saved_list": []}
            return render(request, self.template_name, context)

        saved_status = ReservationStatus.objects.filter(status="保存済み").first()
        if saved_status is None:
            context = {"customer": customer, "saved_list": []}
            return render(request, self.template_name, context)

        reservator = Reservator.objects.filter(customer_account=customer).first()
        if reservator is None:
            context = {"customer": customer, "saved_list": []}
            return render(request, self.template_name, context)

        saved_list = (
            Reservation.objects
            .select_related("store", "booking_status")
            .filter(booking_user=reservator, booking_status=saved_status)
            .order_by("-created_at")
        )

        context = {
            "customer": customer,
            "customer_id": customer.pk,
            "saved_list": saved_list,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        customer = self._get_customer(request)

        # customer が取れない場合は一覧へ戻す
        if customer is None:
            messages.error(request, "ユーザー情報が取得できませんでした。")
            return redirect(reverse("reviews:customer_store_preserve"))

        # ---- 保存解除 ----
        if action == "remove_store":
            reservation_id = request.POST.get("reservation_id")

            if reservation_id:
                deleted, _ = Reservation.objects.filter(
                    id=reservation_id,
                    booking_user__customer_account=customer,
                    booking_status__status="保存済み",
                ).delete()

                if deleted > 0:
                    messages.success(request, "保存解除しました。")
                else:
                    messages.warning(request, "対象の保存データが見つかりませんでした。")
            else:
                messages.warning(request, "保存解除に必要な情報が不足しています。")

            return redirect(f"{reverse('reviews:customer_store_preserve')}?customer_id={customer.pk}")

        # それ以外のPOSTはGETへ
        return redirect(f"{reverse('reviews:customer_store_preserve')}?customer_id={customer.pk}")

class customer_reviewer_review_listView(TemplateView):
    template_name = "reviews/customer_reviewer_review_list.html"

class customer_reviewer_detail_selfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return redirect(reverse("reviews:customer_reviewer_detail", args=[request.user.pk]))


class customer_reviewer_detailView(View):
    template_name = "reviews/customer_reviewer_detail.html"

    def _get_customer(self, request):
        """
        ログイン未実装前提：
        - ?customer_id=xx があればそれを優先
        - なければ CustomerAccount の先頭1件
        - それも無ければ None
        """
        cid = request.GET.get("customer_id") or request.POST.get("customer_id")
        if cid:
            customer = CustomerAccount.objects.filter(pk=cid).first()
            if customer:
                return customer

        return CustomerAccount.objects.order_by("pk").first()

    def get(self, request, *args, **kwargs):
        customer = self._get_customer(request)

        # CustomerAccount が1件も無い場合でも落とさない
        if customer is None:
            context = {
                "customer": None,
                "user_name": "ゲスト",
                "cover_image_url": "",
                "user_icon_url": "",
                "stats_reviews": 0,
                "stats_photos": 0,
                "stats_visitors": 0,
                "stats_likes": 0,
                "count_reviews": 0,
                "count_following": 0,
                "count_followers": 0,
            }
            return render(request, self.template_name, context)

        cover_field = getattr(customer, "cover_image", None)
        icon_field = getattr(customer, "icon_image", None)

        context = {
            "customer": customer,
            "user_name": customer.nickname,
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
        customer = self._get_customer(request)
        if customer is None:
            # そもそも更新対象がない
            return redirect(reverse("reviews:customer_reviewer_detail"))

        # ✅ カバー更新
        if request.FILES.get("cover_image") and hasattr(customer, "cover_image"):
            customer.cover_image = request.FILES["cover_image"]
            customer.save()

        # ✅ アイコン更新
        if request.FILES.get("icon_image") and hasattr(customer, "icon_image"):
            customer.icon_image = request.FILES["icon_image"]
            customer.save()

        # 更新後も同じ人を見せたい（customer_id を維持）
        return redirect(f"{reverse('reviews:customer_reviewer_detail')}?customer_id={customer.pk}")


class customer_reviewer_searchView(TemplateView):
    template_name = "reviews/customer_reviewer_search.html"


class customer_review_reportView(TemplateView):
    template_name = "reviews/customer_review_report.html"


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
        


class customer_report_input(TemplateView):
    template_name = "reviews/customer_report_input.html"


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
