from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Sum
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic.base import TemplateView

# モデルはすべて commons にある前提
from commons.models import StoreAccount, Store, Reservation, StoreOnlineReservation


# ----------------------------
# 共通：storeの取り方（本番のみ）
# ----------------------------
def _get_store_from_user(request: HttpRequest) -> Store:
    """
    ログイン中ユーザーから店舗(Store)を特定
    StoreAccount は Account を継承している前提（pkは user.pk と一致）
    """
    user = request.user
    if not user or not user.is_authenticated:
        raise Http404("ログインしてください。")

    # ここは request.user.storeaccount が一番安全（OneToOneでぶら下がってる想定）
    try:
        sa = user.storeaccount  # type: ignore[attr-defined]
        sa.store  # 念のため
        return sa.store
    except Exception:
        # storeaccount が無い（店舗アカウントではない）
        raise Http404("店舗アカウントではありません。")


# ----------------------------
# カレンダー系ヘルパ
# ----------------------------
def _parse_year_month(request: HttpRequest) -> tuple[int, int]:
    today = timezone.localdate()
    try:
        y = int(request.GET.get("year", today.year))
        m = int(request.GET.get("month", today.month))
    except (TypeError, ValueError):
        y, m = today.year, today.month
    y = max(1970, min(2100, y))
    m = max(1, min(12, m))
    return y, m


def _month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + (month == 12), (month % 12) + 1, 1)  # 翌月1日（排他的）
    return start, end


def _build_month_weeks(year: int, month: int) -> list[list[date]]:
    cal = calendar.Calendar(firstweekday=0)  # 月曜開始
    return cal.monthdatescalendar(year, month)


# ----------------------------
# 台帳：日付パース
# ----------------------------
def _parse_target_date(request: HttpRequest) -> date:
    """?date=YYYY-MM-DD があればそれ、なければ今日"""
    today = timezone.localdate()
    s = request.GET.get("date")
    if not s:
        return today
    try:
        return date.fromisoformat(s)
    except ValueError:
        return today


def _time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


@dataclass
class LedgerBar:
    reservation_id: int
    title: str
    start: time
    end: time
    left_pct: float
    width_pct: float
    visit_count: int
    status_label: str
    top_px: int = 16


def _build_day_bars(
    reservations: list[Reservation],
    *,
    day_start: time = time(11, 0),
    day_end: time = time(23, 0),
) -> tuple[list[LedgerBar], list[str]]:
    """
    日別台帳の横棒データ（start_time / end_time 版）
    - start_time/end_time を使う（visit_time は使わない）
    - 表示は day_start〜day_end にクリップ
    """
    start_min = _time_to_minutes(day_start)
    end_min = _time_to_minutes(day_end)
    span = max(1, end_min - start_min)

    # ヘッダー（11〜22）
    labels = [f"{h:02d}:00" for h in range(day_start.hour, day_end.hour)]
    bars: list[LedgerBar] = []

    for r in reservations:
        st = getattr(r, "start_time", None)
        ed = getattr(r, "end_time", None)

        # もしNULLなどが混ざっても落とさない（基本は必須のはず）
        if not isinstance(st, time) or not isinstance(ed, time):
            continue

        st_min = _time_to_minutes(st)
        ed_min = _time_to_minutes(ed)

        # end が start より小さい（=日跨ぎ）ケースは一旦「当日表示は start から day_end まで」に寄せる
        # ※ 日跨ぎ予約を真面目に表示したいなら別設計が必要
        if ed_min <= st_min:
            ed_min = end_min

        clip_st = max(start_min, min(end_min, st_min))
        clip_ed = max(start_min, min(end_min, ed_min))

        left = (clip_st - start_min) / span * 100.0
        width = max(2.0, (clip_ed - clip_st) / span * 100.0)

        booking_name = getattr(getattr(r, "booking_user", None), "full_name", None) or "予約"
        status_label = str(getattr(r, "booking_status", "") or "")

        bars.append(
            LedgerBar(
                reservation_id=r.id,
                title=booking_name,
                start=st,
                end=time(ed_min // 60, ed_min % 60),
                left_pct=left,
                width_pct=width,
                visit_count=int(getattr(r, "visit_count", 0) or 0),
                status_label=status_label,
            )
        )

    return bars, labels


def _assign_bars_to_fixed_lanes(
    bars: list[LedgerBar],
    *,
    lane_count: int = 3,
    base_top: int = 14,
    row_height: int = 46,
    min_lane_height: int = 120,
    bottom_pad: int = 18,
) -> list[dict[str, Any]]:
    """
    bars を lane_count 本の固定レーンに割り当てる。
    同一レーン内で重なる場合は「縦に積む」
    """
    lane_row_ends: list[list[int]] = [[] for _ in range(lane_count)]
    lane_bars: list[list[LedgerBar]] = [[] for _ in range(lane_count)]

    def to_min(t: time) -> int:
        return t.hour * 60 + t.minute

    bars_sorted = sorted(bars, key=lambda b: (to_min(b.start), to_min(b.end), b.reservation_id))

    for b in bars_sorted:
        st = to_min(b.start)
        ed = to_min(b.end)

        placed_lane: int | None = None
        placed_row: int | None = None

        # 既存rowに入れるか探索（lane優先）
        for li in range(lane_count):
            for ri, row_end in enumerate(lane_row_ends[li]):
                if st >= row_end:
                    placed_lane = li
                    placed_row = ri
                    break
            if placed_lane is not None:
                break

        # 入らないなら row数が少ないlaneへ新row
        if placed_lane is None:
            placed_lane = min(range(lane_count), key=lambda i: len(lane_row_ends[i]))
            placed_row = len(lane_row_ends[placed_lane])
            lane_row_ends[placed_lane].append(-1)

        lane_row_ends[placed_lane][placed_row] = ed
        b.top_px = base_top + placed_row * row_height
        lane_bars[placed_lane].append(b)

    lanes: list[dict[str, Any]] = []
    for i in range(lane_count):
        row_count = max(1, len(lane_row_ends[i]))
        height = max(min_lane_height, base_top + row_count * row_height + bottom_pad)
        lanes.append({"label": f"席レーン{i+1}", "height": height, "bars": lane_bars[i]})
    return lanes


# ----------------------------
# 予約台帳トップ（本番）→ 今日へ
# ----------------------------
class store_reservation_ledgerView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_reservation_ledger.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        today = timezone.localdate()
        return redirect(f"{reverse('reservations_management:store_reservation_ledger_day')}?date={today.isoformat()}")


# ----------------------------
# 予約台帳（日別）本番
# ----------------------------
class store_reservation_ledger_dayView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_reservation_ledger.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)

        store = _get_store_from_user(self.request)
        target_date = _parse_target_date(self.request)

        reservations = list(
            Reservation.objects.filter(store=store, visit_date=target_date)
            .select_related("booking_user", "booking_status")
            .order_by("start_time")
        )

        bars, time_labels = _build_day_bars(reservations)
        lanes = _assign_bars_to_fixed_lanes(bars, lane_count=3)

        prev_date = target_date - timedelta(days=1)
        next_date = target_date + timedelta(days=1)

        ctx.update(
            {
                "mode": "day",
                "store": store,
                "target_date": target_date,
                "prev_date": prev_date,
                "next_date": next_date,
                "bars": bars,
                "lanes": lanes,
                "time_labels": time_labels,
                "time_segments": max(1, len(time_labels)),
            }
        )
        return ctx


# ----------------------------
# 予約詳細（本番）
# ----------------------------
class store_reservation_detailView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_reservation_ledger.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)

        store = _get_store_from_user(self.request)
        pk = kwargs.get("pk")

        try:
            r = Reservation.objects.select_related("store", "booking_user", "booking_status").get(pk=pk, store=store)
        except Reservation.DoesNotExist:
            raise Http404("予約が見つかりません。")

        ctx.update({"mode": "detail", "store": store, "reservation": r})
        return ctx


# ----------------------------
# 予約編集（本番：GET/POST）
# ----------------------------
class store_reservation_editView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_reservation_ledger.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        store = _get_store_from_user(self.request)
        pk = kwargs.get("pk")

        try:
            r = Reservation.objects.select_related("store", "booking_user", "booking_status").get(pk=pk, store=store)
        except Reservation.DoesNotExist:
            raise Http404("予約が見つかりません。")

        ctx.update({"mode": "edit", "store": store, "reservation": r})
        return ctx

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        store = _get_store_from_user(request)
        pk = kwargs.get("pk")

        try:
            r = Reservation.objects.get(pk=pk, store=store)
        except Reservation.DoesNotExist:
            raise Http404("予約が見つかりません。")

        visit_date_s = request.POST.get("visit_date", "")
        start_time_s = request.POST.get("start_time", "")
        end_time_s = request.POST.get("end_time", "")
        visit_count_s = request.POST.get("visit_count", "")

        try:
            new_date = date.fromisoformat(visit_date_s)
            new_start = time.fromisoformat(start_time_s)
            new_end = time.fromisoformat(end_time_s)
            new_count = int(visit_count_s)

            if new_count <= 0:
                raise ValueError("人数は1以上で入力してください。")
            if _time_to_minutes(new_end) <= _time_to_minutes(new_start):
                raise ValueError("終了時刻は開始時刻より後にしてください。")

            r.visit_date = new_date
            r.start_time = new_start
            r.end_time = new_end
            r.visit_count = new_count
            r.save()

            messages.success(request, "予約内容を更新しました。")
        except Exception as e:
            messages.error(request, f"更新に失敗しました：{e}")

        return redirect("reservations_management:store_reservation_detail", pk=pk)


# ----------------------------
# 予約ステータス更新ヘルパ
# ----------------------------
def _set_booking_status_safely(reservation: Reservation, action: str) -> None:
    if action not in ("cancel", "visited"):
        raise ValueError("invalid action")

    desired_tokens = {
        "cancel": ["キャンセル", "cancel", "canceled", "cancelled"],
        "visited": ["来店済み", "来店", "visited", "done", "complete", "completed"],
    }[action]

    field = Reservation._meta.get_field("booking_status")

    # FK
    if field.is_relation and getattr(field, "many_to_one", False):
        rel_model = field.remote_field.model  # type: ignore[attr-defined]
        qs = rel_model.objects.all()

        candidate_fields = ["status", "name", "label", "title", "code", "key"]

        found_obj = None
        for f in candidate_fields:
            if any(ff.name == f for ff in rel_model._meta.fields):
                for token in desired_tokens:
                    obj = qs.filter(**{f"{f}__iexact": token}).first()
                    if obj:
                        found_obj = obj
                        break
            if found_obj:
                break

        if not found_obj:
            for f in candidate_fields:
                if any(ff.name == f for ff in rel_model._meta.fields):
                    for token in desired_tokens:
                        obj = qs.filter(**{f"{f}__icontains": token}).first()
                        if obj:
                            found_obj = obj
                            break
                if found_obj:
                    break

        if not found_obj:
            raise ValueError(f"booking_status(FK) の参照先 {rel_model.__name__} に {desired_tokens} が見つかりません。")

        setattr(reservation, "booking_status", found_obj)
        return

    # choices
    choices = getattr(field, "choices", None) or []
    if choices:
        for value, label in choices:
            for token in desired_tokens:
                if str(label) == token:
                    setattr(reservation, "booking_status", value)
                    return
        for value, label in choices:
            for token in desired_tokens:
                if str(value) == token:
                    setattr(reservation, "booking_status", value)
                    return
        raise ValueError(f"booking_status(choices) に一致がありません。 choices={list(choices)}")

    raise ValueError("booking_status の型が不明です（FKでもchoicesでもない）。")


# ----------------------------
# 予約ステータス変更（本番：POST）
# ----------------------------
class store_reservation_actionView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        pk = kwargs.get("pk")
        action = request.POST.get("action")

        if action not in ("cancel", "visited"):
            messages.error(request, "不正な操作です。")
            return redirect("reservations_management:store_reservation_detail", pk=pk)

        store = _get_store_from_user(request)

        try:
            r = Reservation.objects.select_related("store", "booking_status").get(pk=pk, store=store)
        except Reservation.DoesNotExist:
            raise Http404("予約が見つかりません。")

        try:
            with transaction.atomic():
                _set_booking_status_safely(r, action)
                r.save()
            messages.success(request, "予約ステータスを更新しました。")
        except Exception as e:
            messages.error(request, f"更新に失敗しました：{e}")

        return redirect("reservations_management:store_reservation_detail", pk=pk)


# ----------------------------
# 顧客台帳・席設定（とりあえずTemplateView）
# ----------------------------
class store_customer_ledgerView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_customer_ledger.html"


class store_seat_settingsView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_seat_settings.html"


# ----------------------------
# 予約カレンダー（本番）
# ----------------------------
class store_reservation_calendarView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_reservation_calendar.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)

        store = _get_store_from_user(self.request)
        year, month = _parse_year_month(self.request)
        weeks = _build_month_weeks(year, month)
        month_start, month_end = _month_range(year, month)

        qs = (
            Reservation.objects.filter(store=store, visit_date__gte=month_start, visit_date__lt=month_end)
            .values("visit_date")
            .annotate(groups=Count("id"), people=Sum("visit_count"))
            .order_by("visit_date")
        )
        daily = {row["visit_date"]: {"groups": row["groups"], "people": int(row["people"] or 0)} for row in qs}

        online_qs = (
            StoreOnlineReservation.objects.filter(store=store, date__gte=month_start, date__lt=month_end)
            .values("date", "booking_status", "available_seats")
        )
        online = {
            row["date"]: {"is_open": bool(row["booking_status"]), "available_seats": int(row["available_seats"] or 0)}
            for row in online_qs
        }

        today = timezone.localdate()
        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

        ctx.update(
            {
                "store": store,
                "year": year,
                "month": month,
                "month_label": f"{year}年 {month}月",
                "weeks": weeks,
                "today": today,
                "prev_year": prev_year,
                "prev_month": prev_month,
                "next_year": next_year,
                "next_month": next_month,
                "daily": daily,
                "online": online,
                "closed_days": set(),
            }
        )
        return ctx


# ----------------------------
# 受付設定（本番）
# ----------------------------
class store_reservation_settingsView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_reservation_settings.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)

        store = _get_store_from_user(self.request)
        year, month = _parse_year_month(self.request)
        weeks = _build_month_weeks(year, month)
        month_start, month_end = _month_range(year, month)

        online_qs = (
            StoreOnlineReservation.objects.filter(store=store, date__gte=month_start, date__lt=month_end)
            .values("date", "booking_status", "available_seats")
        )
        online = {
            row["date"]: {"is_open": bool(row["booking_status"]), "available_seats": int(row["available_seats"] or 0)}
            for row in online_qs
        }

        today = timezone.localdate()
        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

        ctx.update(
            {
                "store": store,
                "year": year,
                "month": month,
                "month_label": f"{year}年 {month}月",
                "weeks": weeks,
                "today": today,
                "prev_year": prev_year,
                "prev_month": prev_month,
                "next_year": next_year,
                "next_month": next_month,
                "online": online,
                "closed_days": set(),
            }
        )
        return ctx

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        store = _get_store_from_user(request)

        year, month = _parse_year_month(request)
        month_start, month_end = _month_range(year, month)

        action = request.POST.get("action", "")

        # ==========================================
        # ★ 追加：表示中の月を一括で「受付中」にする
        # ==========================================
        if action == "bulk_open":
            default_seats = int(getattr(store, "seats", 0) or 0)

            d = month_start
            while d < month_end:
                StoreOnlineReservation.objects.update_or_create(
                    store=store,
                    date=d,
                    defaults={"booking_status": True, "available_seats": default_seats},
                )
                d += timedelta(days=1)

            messages.success(request, f"{year}年{month}月をすべて『受付中』にしました。")
            return redirect(f"{reverse('reservations_management:store_reservation_settings')}?year={year}&month={month}")

        # ==========================================
        # 既存：日別の設定を保存する
        # ==========================================
        date_str = request.POST.get("date", "")
        day_type = request.POST.get("day_type", "open")
        booking_status = request.POST.get("booking_status", "0")
        available_seats_str = request.POST.get("available_seats", "")

        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            messages.error(request, "日付が不正です。")
            return redirect(f"{reverse('reservations_management:store_reservation_settings')}?year={year}&month={month}")

        if not (month_start <= target_date < month_end):
            messages.error(request, "この月以外の日付は設定できません。")
            return redirect(f"{reverse('reservations_management:store_reservation_settings')}?year={year}&month={month}")

        if day_type == "closed":
            is_open = False
            available_seats = 0
        else:
            is_open = (booking_status == "1")
            if available_seats_str == "":
                messages.error(request, "空き席数は必須です（営業日の場合）。")
                return redirect(f"{reverse('reservations_management:store_reservation_settings')}?year={year}&month={month}")
            try:
                available_seats = int(available_seats_str)
            except ValueError:
                messages.error(request, "空き席数は数字で入力してください。")
                return redirect(f"{reverse('reservations_management:store_reservation_settings')}?year={year}&month={month}")
            if available_seats < 0:
                messages.error(request, "空き席数は0以上で入力してください。")
                return redirect(f"{reverse('reservations_management:store_reservation_settings')}?year={year}&month={month}")

        StoreOnlineReservation.objects.update_or_create(
            store=store,
            date=target_date,
            defaults={"booking_status": is_open, "available_seats": available_seats},
        )
        messages.success(request, f"{target_date} の設定を保存しました。")
        return redirect(f"{reverse('reservations_management:store_reservation_settings')}?year={year}&month={month}")
