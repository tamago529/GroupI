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

# モデルは commons
from commons.models import Store, Reservation, StoreOnlineReservation, ReservationStatus


# ============================================================
# コース（分）定義
# ============================================================
COURSE_MINUTES_CHOICES: list[int] = [30, 60, 90, 120, 150]


def _course_label(minutes: int) -> str:
    if minutes == 30:
        return "30分コース"
    if minutes == 60:
        return "1時間コース"
    if minutes == 90:
        return "1時間30分コース"
    if minutes == 120:
        return "2時間コース"
    if minutes == 150:
        return "2時間30分コース"
    return f"{minutes}分コース"


# ============================================================
# 営業時間ヘルパ（Store.open/close 1・2枠）
# ============================================================
@dataclass(frozen=True)
class TimeInterval:
    start: time
    end: time


def _time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _minutes_to_time(m: int) -> time:
    m = max(0, min(24 * 60 - 1, m))
    return time(m // 60, m % 60)


def _get_store_intervals(store: Store) -> list[TimeInterval]:
    """
    Store の open/close から営業時間区間を返す（最大2区間）
    - start>=end は無効として捨てる
    """
    intervals: list[TimeInterval] = []

    def push(a: time | None, b: time | None) -> None:
        if isinstance(a, time) and isinstance(b, time) and _time_to_minutes(b) > _time_to_minutes(a):
            intervals.append(TimeInterval(a, b))

    push(store.open_time_1, store.close_time_1)
    push(store.open_time_2, store.close_time_2)

    intervals.sort(key=lambda x: _time_to_minutes(x.start))
    return intervals


def _build_closed_ranges(intervals: list[TimeInterval]) -> list[TimeInterval]:
    """
    営業時間レンジ内の「中休み」区間を返す
    例: (11-15),(17-22) -> (15-17)
    """
    if len(intervals) < 2:
        return []
    closed: list[TimeInterval] = []
    for i in range(len(intervals) - 1):
        a_end = intervals[i].end
        b_start = intervals[i + 1].start
        if _time_to_minutes(b_start) > _time_to_minutes(a_end):
            closed.append(TimeInterval(a_end, b_start))
    return closed


def _is_inside_one_interval(start: time, end: time, intervals: list[TimeInterval]) -> bool:
    """
    予約の開始〜終了が「どれか1つの営業時間区間」に完全に収まるか
    中休みをまたぐのはNG
    """
    s = _time_to_minutes(start)
    e = _time_to_minutes(end)

    # 日跨ぎ（end <= start）はNG（このシステムでは想定しない）
    if e <= s:
        return False

    for itv in intervals:
        a = _time_to_minutes(itv.start)
        b = _time_to_minutes(itv.end)
        if a <= s and e <= b:
            return True
    return False


def _ledger_range_from_intervals(intervals: list[TimeInterval]) -> tuple[time, time]:
    """
    台帳の表示レンジ（最小start〜最大end）
    intervals が無い場合は 11-23 を返す
    """
    if not intervals:
        return time(11, 0), time(23, 0)
    start = min(i.start for i in intervals)
    end = max(i.end for i in intervals)
    if _time_to_minutes(end) <= _time_to_minutes(start):
        return time(11, 0), time(23, 0)
    return start, end


def _build_time_labels(day_start: time, day_end: time, step_min: int = 30) -> list[str]:
    """
    例: 11:00〜23:00 を 30分刻みで ['11:00','11:30',...,'22:30','23:00']
    """
    a = _time_to_minutes(day_start)
    b = _time_to_minutes(day_end)
    if b <= a:
        return ["11:00", "23:00"]

    labels: list[str] = []
    t = a
    while t <= b:
        labels.append(f"{t // 60:02d}:{t % 60:02d}")
        t += step_min
    return labels


# ============================================================
# 共通：storeの取り方（本番のみ）
# ============================================================
def _get_store_from_user(request: HttpRequest) -> Store:
    """
    ログイン中ユーザーから店舗(Store)を特定
    StoreAccount は Account を継承している前提（pkは user.pk と一致）
    """
    user = request.user
    if not user or not user.is_authenticated:
        raise Http404("ログインしてください。")

    try:
        sa = user.storeaccount  # type: ignore[attr-defined]
        sa.store
        return sa.store
    except Exception:
        raise Http404("店舗アカウントではありません。")


# ============================================================
# カレンダー系ヘルパ
# ============================================================
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
    end = date(year + (month == 12), (month % 12) + 1, 1)
    return start, end


def _build_month_weeks(year: int, month: int) -> list[list[date]]:
    cal = calendar.Calendar(firstweekday=0)  # 月曜開始
    return cal.monthdatescalendar(year, month)


# ============================================================
# 台帳：日付パース
# ============================================================
def _parse_target_date(request: HttpRequest) -> date:
    today = timezone.localdate()
    s = request.GET.get("date")
    if not s:
        return today
    try:
        return date.fromisoformat(s)
    except ValueError:
        return today


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
    course: str = ""
    top_px: int = 16


def _build_day_bars_and_closed_bands(
    reservations: list[Reservation],
    *,
    store: Store,
    step_min: int = 30,
) -> tuple[list[LedgerBar], list[str], list[dict[str, float]], time, time]:
    """
    日別台帳の横棒（start_time/end_time）＋ 中休み帯
    - 表示レンジは storeの営業時間から自動算出（未設定なら 11-23）
    - bars は表示レンジにクリップして left/width を計算
    - 中休み帯は closed_bands（left_pct/width_pct）で返す
    """
    intervals = _get_store_intervals(store)
    day_start, day_end = _ledger_range_from_intervals(intervals)

    start_min = _time_to_minutes(day_start)
    end_min = _time_to_minutes(day_end)
    span = max(1, end_min - start_min)

    time_labels = _build_time_labels(day_start, day_end, step_min=step_min)

    # 中休み帯（営業時間レンジ基準）
    closed_ranges = _build_closed_ranges(intervals)
    closed_bands: list[dict[str, float]] = []
    for itv in closed_ranges:
        left = (_time_to_minutes(itv.start) - start_min) / span * 100.0
        width = (_time_to_minutes(itv.end) - _time_to_minutes(itv.start)) / span * 100.0
        if width > 0:
            closed_bands.append({"left_pct": left, "width_pct": width})

    bars: list[LedgerBar] = []

    for r in reservations:
        st = getattr(r, "start_time", None)
        ed = getattr(r, "end_time", None)

        if not isinstance(st, time) or not isinstance(ed, time):
            continue

        st_min = _time_to_minutes(st)
        ed_min = _time_to_minutes(ed)

        # 日跨ぎは当日表示では末尾までに丸める（表示だけの措置）
        if ed_min <= st_min:
            ed_min = end_min

        clip_st = max(start_min, min(end_min, st_min))
        clip_ed = max(start_min, min(end_min, ed_min))

        # レンジ外しか無いものは非表示
        if clip_ed <= clip_st:
            continue

        left = (clip_st - start_min) / span * 100.0
        width = max(2.0, (clip_ed - clip_st) / span * 100.0)

        booking_name = getattr(getattr(r, "booking_user", None), "full_name", None) or "予約"
        status_label = str(getattr(r, "booking_status", "") or "")

        course_text = str(getattr(r, "course", "") or "")

        bars.append(
            LedgerBar(
                reservation_id=r.id,
                title=booking_name,
                start=st,
                end=_minutes_to_time(ed_min),
                left_pct=left,
                width_pct=width,
                visit_count=int(getattr(r, "visit_count", 0) or 0),
                status_label=status_label,
                course=course_text,
            )
        )

    return bars, time_labels, closed_bands, day_start, day_end


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
        return _time_to_minutes(t)

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


# ============================================================
# 予約台帳トップ → 今日へ
# ============================================================
class store_reservation_ledgerView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_reservation_ledger.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        today = timezone.localdate()
        return redirect(f"{reverse('reservations_management:store_reservation_ledger_day')}?date={today.isoformat()}")


# ============================================================
# 予約台帳（日別）
# ============================================================
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

        bars, time_labels, closed_bands, day_start, day_end = _build_day_bars_and_closed_bands(
            reservations, store=store, step_min=30
        )
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
                # ★営業時間レンジ
                "day_start": day_start,
                "day_end": day_end,
                # ★中休み帯
                "closed_bands": closed_bands,
            }
        )
        return ctx


# ============================================================
# 予約詳細
# ============================================================
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


# ============================================================
# 予約編集（店舗側：GET/POST）
# ============================================================
class store_reservation_editView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_reservation_ledger.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        store = _get_store_from_user(self.request)
        pk = kwargs.get("pk")

        try:
            r = (
                Reservation.objects.select_related("store", "booking_user", "booking_status")
                .get(pk=pk, store=store)
            )
        except Reservation.DoesNotExist:
            raise Http404("予約が見つかりません。")

        status_choices = ReservationStatus.objects.all().order_by("status", "id")

        ctx.update(
            {
                "mode": "edit",
                "store": store,
                "reservation": r,
                "status_choices": status_choices,
                # ★テンプレでセレクト出したい時用（今回のテンプレJSは固定で option を出してるけど、将来用に渡しておく）
                "course_minutes_choices": COURSE_MINUTES_CHOICES,
            }
        )
        return ctx

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        store = _get_store_from_user(request)
        pk = kwargs.get("pk")

        try:
            r = Reservation.objects.select_related("booking_status").get(pk=pk, store=store)
        except Reservation.DoesNotExist:
            raise Http404("予約が見つかりません。")

        visit_date_s = (request.POST.get("visit_date") or "").strip()
        start_time_s = (request.POST.get("start_time") or "").strip()
        end_time_s = (request.POST.get("end_time") or "").strip()
        visit_count_s = (request.POST.get("visit_count") or "").strip()
        booking_status_id_s = (request.POST.get("booking_status_id") or "").strip()

        # ★追加：テンプレから送られる（空なら「変更しない」）
        course_minutes_s = (request.POST.get("course_minutes") or "").strip()

        try:
            new_date = date.fromisoformat(visit_date_s)
            new_start = time.fromisoformat(start_time_s)
            new_count = int(visit_count_s)

            if new_count <= 0:
                raise ValueError("人数は1以上で入力してください。")

            # -------------------------
            # 終了時刻：course_minutes が来たら自動計算、無ければ end_time を採用
            # -------------------------
            if course_minutes_s:
                try:
                    course_minutes = int(course_minutes_s)
                except Exception:
                    raise ValueError("コース時間が不正です。")

                if course_minutes not in COURSE_MINUTES_CHOICES:
                    raise ValueError("コース時間が不正です。")

                end_dt = datetime.combine(new_date, new_start) + timedelta(minutes=course_minutes)

                # 日跨ぎNG（この台帳は当日内のみ）
                if end_dt.date() != new_date:
                    raise ValueError("終了時刻が翌日になるため保存できません。")

                new_end = end_dt.time()
                new_course = _course_label(course_minutes)
            else:
                # 既存通り：終了時刻の手入力
                new_end = time.fromisoformat(end_time_s)
                if _time_to_minutes(new_end) <= _time_to_minutes(new_start):
                    raise ValueError("終了時刻は開始時刻より後にしてください。")

                # コース文字列は「変更しない」（現状維持）
                new_course = None  # type: ignore[assignment]

            # ★営業時間チェック（中休み跨ぎも弾く）
            intervals = _get_store_intervals(store)
            if not intervals:
                raise ValueError("営業時間が未設定のため更新できません。")
            if not _is_inside_one_interval(new_start, new_end, intervals):
                raise ValueError("営業時間外、または中休みをまたぐ時間帯は設定できません。")

            # ステータスIDが来ている場合のみ更新
            new_status = None
            if booking_status_id_s:
                try:
                    new_status_id = int(booking_status_id_s)
                except Exception:
                    raise ValueError("ステータスが不正です。")

                new_status = ReservationStatus.objects.filter(pk=new_status_id).first()
                if not new_status:
                    raise ValueError("選択されたステータスが見つかりません。")

            with transaction.atomic():
                r.visit_date = new_date
                r.start_time = new_start
                r.end_time = new_end
                r.visit_time = new_start  # ★整合：visit_timeも開始に合わせる
                r.visit_count = new_count

                # ★コースを選んだ場合だけ更新（選ばなければ現状維持）
                if course_minutes_s:
                    r.course = new_course  # type: ignore[arg-type]

                if new_status is not None:
                    r.booking_status = new_status

                r.save()

            messages.success(request, "予約内容を更新しました。")

        except Exception as e:
            messages.error(request, f"更新に失敗しました：{e}")

        return redirect("reservations_management:store_reservation_detail", pk=pk)


# ============================================================
# 予約ステータス更新ヘルパ
# ============================================================
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
            raise ValueError(
                f"booking_status(FK) の参照先 {rel_model.__name__} に {desired_tokens} が見つかりません。"
            )

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


# ============================================================
# 予約ステータス変更（POST）
# ============================================================
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


# ============================================================
# 顧客台帳・席設定（TemplateView）
# ============================================================
class store_customer_ledgerView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_customer_ledger.html"


class store_seat_settingsView(LoginRequiredMixin, TemplateView):
    template_name = "reservations_management/store_seat_settings.html"


# ============================================================
# 予約カレンダー
# ============================================================
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
                "next_month": next_year if False else next_month,  # 互換のため（不要なら消してOK）
                "daily": daily,
                "online": online,
                "closed_days": set(),
            }
        )
        # ↑ next_year の上で next_month を変にしてたので正しく上書き
        ctx["next_year"] = next_year
        ctx["next_month"] = next_month
        return ctx


# ============================================================
# 受付設定
# ============================================================
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

        # ★表示中の月を一括で「受付中」
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

        # 既存：日別設定
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
