from __future__ import annotations

from datetime import date, time

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from commons.models import CustomerAccount, Reservation, ReservationStatus


# ----------------------------
# 共通ヘルパ
# ----------------------------
def _get_customer_user(request: HttpRequest) -> CustomerAccount:
    if not request.user.is_authenticated:
        raise Http404("ログインしてください。")
    if not isinstance(request.user, CustomerAccount):
        raise Http404("顧客アカウントではありません。")
    return request.user


def _get_customer_reservation(customer: CustomerAccount, reservation_id: int) -> Reservation:
    """
    顧客に紐づく予約のみ取得（Reservator.customer_account 経由）
    """
    r = (
        Reservation.objects.select_related("store", "booking_user", "booking_status")
        .filter(id=reservation_id, booking_user__customer_account=customer)
        .first()
    )
    if not r:
        raise Http404("予約が見つかりません。")
    return r


def _get_store_page_url(store_id: int) -> str:
    """
    店舗ページURLがプロジェクト内にある場合はここで reverse する。
    無い場合でも画面が壊れないように # にフォールバック。
    """
    try:
        # もし店舗詳細が存在するなら、ここをあなたの実URL名に合わせて変更
        # 例: return reverse("stores:store_detail", args=[store_id])
        return "#"
    except Exception:
        return "#"


def _set_reservation_status_cancelled(reservation: Reservation) -> None:
    """
    Reservation.booking_status (FK) を「キャンセル」に寄せる
    """
    desired_tokens = ["キャンセル", "cancel", "canceled", "cancelled"]

    qs = ReservationStatus.objects.all()
    found = None
    for token in desired_tokens:
        found = qs.filter(status__iexact=token).first()
        if found:
            break
    if not found:
        # 部分一致も試す
        for token in desired_tokens:
            found = qs.filter(status__icontains=token).first()
            if found:
                break

    if not found:
        raise ValueError("ReservationStatus に「キャンセル」が見つかりません。")

    reservation.booking_status = found




# ----------------------------
# 予約履歴
# ----------------------------
class store_reservation_historyView(LoginRequiredMixin, TemplateView):
    template_name = "reservations/store_reservation_history.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = _get_customer_user(self.request)

        reservations = (
            Reservation.objects.select_related("store", "booking_user", "booking_status")
            .filter(booking_user__customer_account=customer)
            .order_by("-visit_date", "-visit_time", "-id")
        )

        ctx.update(
            {
                "reservations": reservations,
            }
        )
        return ctx


# ----------------------------
# 予約確認（詳細）
# ----------------------------
class store_reservation_confirmView(LoginRequiredMixin, TemplateView):
    template_name = "reservations/store_reservation_confirm.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = _get_customer_user(self.request)

        reservation_id = int(kwargs.get("reservation_id"))
        reservation = _get_customer_reservation(customer, reservation_id)

        store_page_url = _get_store_page_url(reservation.store_id)

        ctx.update(
            {
                "reservation": reservation,
                "store": reservation.store,
                "store_page_url": store_page_url,
            }
        )
        return ctx


# ----------------------------
# 予約変更（GET/POST）
# ----------------------------
class store_reservation_editView(LoginRequiredMixin, TemplateView):
    template_name = "reservations/store_reservation_edit.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = _get_customer_user(self.request)

        reservation_id = int(kwargs.get("reservation_id"))
        reservation = _get_customer_reservation(customer, reservation_id)

        store_page_url = _get_store_page_url(reservation.store_id)

        ctx.update(
            {
                "reservation": reservation,
                "store": reservation.store,
                "store_page_url": store_page_url,
            }
        )
        return ctx

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        customer = _get_customer_user(request)
        reservation_id = int(kwargs.get("reservation_id"))
        reservation = _get_customer_reservation(customer, reservation_id)

        visit_date_s = (request.POST.get("visit_date") or "").strip()
        visit_time_s = (request.POST.get("visit_time") or "").strip()
        visit_count_s = (request.POST.get("visit_count") or "").strip()
        course = (request.POST.get("course") or "").strip()

        errors = []

        # visit_date
        try:
            new_date = date.fromisoformat(visit_date_s)
        except Exception:
            errors.append("来店日が不正です。")
            new_date = reservation.visit_date

        # visit_time
        try:
            new_time = time.fromisoformat(visit_time_s)
        except Exception:
            errors.append("来店時刻が不正です。")
            new_time = reservation.visit_time

        # visit_count
        try:
            new_count = int(visit_count_s)
            if new_count <= 0:
                raise ValueError
        except Exception:
            errors.append("人数は1以上の数字で入力してください。")
            new_count = reservation.visit_count

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect("reservations:store_reservation_edit", reservation_id=reservation.id)

        # 保存
        reservation.visit_date = new_date
        reservation.visit_time = new_time
        reservation.visit_count = new_count
        if course != "":
            reservation.course = course

        reservation.save()
        messages.success(request, "ご予約内容を変更しました。")
        return redirect("reservations:store_reservation_confirm", reservation_id=reservation.id)


# ----------------------------
# 予約キャンセル（GET/POST）
# ----------------------------
class store_reservation_cancelView(LoginRequiredMixin, TemplateView):
    template_name = "reservations/store_reservation_cancel.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = _get_customer_user(self.request)

        reservation_id = int(kwargs.get("reservation_id"))
        reservation = _get_customer_reservation(customer, reservation_id)

        store_page_url = _get_store_page_url(reservation.store_id)

        ctx.update(
            {
                "reservation": reservation,
                "store": reservation.store,
                "store_page_url": store_page_url,
            }
        )
        return ctx

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        customer = _get_customer_user(request)
        reservation_id = int(kwargs.get("reservation_id"))
        reservation = _get_customer_reservation(customer, reservation_id)

        cancel_reason = (request.POST.get("cancel_reason") or "").strip()
        cancel_detail = (request.POST.get("cancel_detail") or "").strip()

        if not cancel_reason or cancel_reason == "選択してください":
            messages.error(request, "キャンセル理由を選択してください。")
            return redirect("reservations:store_reservation_cancel", reservation_id=reservation.id)

        # cancel_reason フィールドは TextField なのでまとめて保存する
        if cancel_detail:
            reservation.cancel_reason = f"{cancel_reason}\n\n{cancel_detail}"
        else:
            reservation.cancel_reason = cancel_reason

        try:
            _set_reservation_status_cancelled(reservation)
        except Exception as e:
            messages.error(request, f"ステータス更新に失敗しました：{e}")
            return redirect("reservations:store_reservation_cancel", reservation_id=reservation.id)

        reservation.save()
        messages.success(request, "予約をキャンセルしました。")
        return redirect("reservations:store_reservation_confirm", reservation_id=reservation.id)
