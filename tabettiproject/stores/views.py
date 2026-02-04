# stores/views.py
from __future__ import annotations

import calendar
import os
import random
import urllib.parse
import requests
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files import File
from django.db import models
from django.db.models import Q, Avg, Count, Sum, F
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import UpdateView
from django.views.generic.base import TemplateView

from commons.models import (
    CustomerAccount,
    Reservation,
    Reservator,
    ReservationStatus,
    Review,
    Store,
    StoreAccount,
    StoreImage,
    StoreMenu,
    StoreOnlineReservation,
    StoreAccessLog,
    Area,
    Scene,
    Genre,
)

from .form import (
    CompanyStoreEditForm,
    CustomerReserveForm,
    StoreBasicForm,
    StoreImageFormSet,
    StoreMenuFormSet,
    StoreRegistrationForm,
)

# ============================================================
# ★ 追加：ID209〜390は「店舗アカウント無しでも」予約機能を有効化
# （今後範囲が増えるならここだけ触ればOK）
# ============================================================
AUTO_RESERVATION_STORE_ID_MIN = 209
AUTO_RESERVATION_STORE_ID_MAX = 390


def _is_auto_reservation_store(store: Store) -> bool:
    sid = int(getattr(store, "pk", 0) or 0)
    return AUTO_RESERVATION_STORE_ID_MIN <= sid <= AUTO_RESERVATION_STORE_ID_MAX


def _default_available_seats(store: Store) -> int:
    # seats が 0/None の場合は “無制限相当” として大きめにする
    seats = int(getattr(store, "seats", 0) or 0)
    return seats if seats > 0 else 999


def has_net_reservation(store: Store) -> bool:
    """
    ネット予約可能か（店舗アカウントあり or ID209-390）
    """
    return StoreAccount.objects.filter(store=store).exists() or _is_auto_reservation_store(store)


def _ensure_online_setting(store: Store, target_date: date) -> StoreOnlineReservation | None:
    """
    ID209-390の店舗は StoreOnlineReservation が未作成でも
    予約を使えるように、必要な日だけ自動で作る（既存なら何もしない）
    """
    if not _is_auto_reservation_store(store):
        return None

    obj = StoreOnlineReservation.objects.filter(store=store, date=target_date).first()
    if obj:
        return obj

    return StoreOnlineReservation.objects.create(
        store=store,
        date=target_date,
        booking_status=True,
        available_seats=_default_available_seats(store),
    )


def _ensure_month_online_settings(store: Store, year: int, month: int) -> None:
    """
    customer_store_info のカレンダー表示用：
    ID209-390店舗は、その月の未来日ぶんの StoreOnlineReservation を
    まとめて自動生成して “open_days が 0件” にならないようにする
    """
    if not _is_auto_reservation_store(store):
        return

    today = timezone.localdate()
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)

    # 未来日だけ
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    dates = [d for d in dates if d >= today]
    if not dates:
        return

    existing = set(
        StoreOnlineReservation.objects.filter(store=store, date__range=(start, end))
        .values_list("date", flat=True)
    )
    to_create = [d for d in dates if d not in existing]
    if not to_create:
        return

    StoreOnlineReservation.objects.bulk_create(
        [
            StoreOnlineReservation(
                store=store,
                date=d,
                booking_status=True,
                available_seats=_default_available_seats(store),
            )
            for d in to_create
        ],
        ignore_conflicts=True,
    )


# ============================================================
# ★追加：ID209〜390 は「メニューが無ければ」自動生成して画像を割り当て
# ============================================================
AUTO_MENU_STORE_ID_MIN = 209
AUTO_MENU_STORE_ID_MAX = 390


def _is_auto_menu_store(store: Store) -> bool:
    sid = int(getattr(store, "pk", 0) or 0)
    return AUTO_MENU_STORE_ID_MIN <= sid <= AUTO_MENU_STORE_ID_MAX


def _get_pool_files(pool_rel: str) -> list[str]:
    """
    pool_rel: BASE_DIR からの相対パス（例: "media/_pool/store/food"）
    """
    pool_rel = (pool_rel or "").strip().replace("\\", "/")
    pool_dir = os.path.join(settings.BASE_DIR, pool_rel)
    if not os.path.isdir(pool_dir):
        return []
    files: list[str] = []
    for f in os.listdir(pool_dir):
        p = os.path.join(pool_dir, f)
        if os.path.isfile(p):
            files.append(p)
    return files


def _ensure_store_menus(
    *,
    store: Store,
    per_store: int = 6,
    pool_rel: str = "media/_pool/store/food",
    rotate: bool = True,
) -> int:
    """
    ID209-390 の店舗は StoreMenu が0件なら自動生成して “メニューがある扱い” にする。
    画像は pool から割り当てて image_file に保存する。

    return: 作成した件数
    """
    if not _is_auto_menu_store(store):
        return 0

    if StoreMenu.objects.filter(store=store).exists():
        return 0

    base_names = [
        "おすすめ盛り合わせ",
        "季節の前菜",
        "お刺身盛り",
        "焼き物",
        "揚げ物",
        "〆の一品",
        "デザート",
        "ドリンク",
    ]

    pool_files = _get_pool_files(pool_rel)  # 無ければ画像なしでも作る

    created = 0
    for i in range(per_store):
        name = base_names[i % len(base_names)]
        price = 700 + (i * 150)

        menu = StoreMenu.objects.create(
            store=store,
            menu_name=name,
            price=price,
            image_path="----",
        )

        # 画像割り当て（プールがある場合だけ）
        if pool_files:
            src = pool_files[i % len(pool_files)] if rotate else random.choice(pool_files)
            with open(src, "rb") as f:
                menu.image_file.save(os.path.basename(src), File(f), save=True)

        created += 1

    return created


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

    push(getattr(store, "open_time_1", None), getattr(store, "close_time_1", None))
    push(getattr(store, "open_time_2", None), getattr(store, "close_time_2", None))

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

    # 日跨ぎ（end <= start）はNG
    if e <= s:
        return False

    for itv in intervals:
        a = _time_to_minutes(itv.start)
        b = _time_to_minutes(itv.end)
        if a <= s and e <= b:
            return True
    return False


def _format_intervals_for_js(intervals: list[TimeInterval]) -> list[dict[str, str]]:
    return [{"start": itv.start.strftime("%H:%M"), "end": itv.end.strftime("%H:%M")} for itv in intervals]


def _course_name(course_minutes: int) -> str:
    course_map = {
        30: "30分コース",
        60: "1時間コース",
        90: "1時間30分コース",
        120: "2時間コース",
        150: "2時間30分コース",
    }
    return course_map.get(course_minutes, f"{course_minutes}分コース")


def _validate_customer_reservation_time(
    *,
    store: Store,
    visit_date: date,
    visit_time: time,
    course_minutes: int,
) -> tuple[bool, str, time | None]:
    """
    顧客予約の「営業時間」検証：
    - 店舗の営業時間が未設定ならNG
    - コース終了が営業時間超え / 中休み跨ぎ はNG
    - 日跨ぎはNG
    戻り値: (ok, reason, end_time)
    """
    intervals = _get_store_intervals(store)
    if not intervals:
        return False, "営業時間が未設定のため予約できません。店舗へお問い合わせください。", None

    if course_minutes not in (30, 60, 90, 120, 150):
        return False, "コースが不正です。", None

    start_dt = datetime.combine(visit_date, visit_time)
    end_dt = start_dt + timedelta(minutes=course_minutes)

    # 日跨ぎNG
    if end_dt.date() != visit_date:
        return False, "営業時間外の予約はできません（終了時刻が翌日になります）。", None

    end_time = end_dt.time()

    # 1区間内に収まる（中休み跨ぎもNG）
    if not _is_inside_one_interval(visit_time, end_time, intervals):
        return False, "営業時間外、または中休みをまたぐ時間帯は予約できません。", None

    return True, "", end_time


# ============================================================
# helper
# ============================================================
def get_store_from_user(user) -> Store | None:
    if not user or not user.is_authenticated:
        return None
    try:
        return user.storeaccount.store
    except Exception:
        return None


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


def _get_customer_from_user(user) -> CustomerAccount | None:
    """
    多テーブル継承対策：
    request.user が Account 型でも pk で CustomerAccount を拾う
    """
    if not user or not user.is_authenticated:
        return None
    if isinstance(user, CustomerAccount):
        return user
    return CustomerAccount.objects.filter(pk=user.pk).first()


# ============================================================
# ★星評価 共通（Storeにavg_rating等が無い前提）
# ============================================================
def build_star_states(avg_rating: float) -> list[str]:
    """
    星のルール（確定）:
    - 2.0 -> ★★☆☆☆
    - 2.5〜2.9 -> ★★☆½☆
    - 2.9以上 -> 繰り上げ（★★★☆☆）
    """
    rating = float(avg_rating or 0.0)
    full = int(rating)
    frac = rating - full

    if frac >= 0.9:
        full += 1
        half = 0
    elif frac >= 0.5:
        half = 1
    else:
        half = 0

    if full >= 5:
        full = 5
        half = 0

    empty = 5 - full - half
    return (["full"] * full) + (["half"] * half) + (["empty"] * empty)


def _get_store_rating_context(store: Store) -> dict[str, object]:
    """
    Reviewから毎回集計してテンプレ用の値を返す
    """
    agg = Review.objects.filter(store=store).aggregate(
        weighted_sum=Sum(F("score") * F("reviewer__trust_score")),
        weight_total=Sum("reviewer__trust_score"),
        avg=Avg("score"),
        cnt=Count("id"),
    )

    # 加重平均を計算（重み合計が0の場合は単純平均、それもなければ0）
    if agg["weight_total"]:
        avg_rating = float(agg["weighted_sum"]) / float(agg["weight_total"])
    else:
        avg_rating = float(agg["avg"] or 0.0)

    # 5.0を超えないようにキャップ（念のため）
    if avg_rating > 5.0:
        avg_rating = 5.0

    review_count = int(agg["cnt"] or 0)
    return {
        "avg_rating": avg_rating,
        "review_count": review_count,
        "star_states": build_star_states(avg_rating),
    }


def _get_is_saved_for_customer(*, customer: CustomerAccount | None, store: Store) -> bool:
    """
    共通ヘッダー用：保存済み判定（ログイン顧客のみ）
    """
    if not customer:
        return False
    saved_status = ReservationStatus.objects.filter(status="保存済み").first()
    if not saved_status:
        return False
    reservator = Reservator.objects.filter(customer_account=customer).first()
    if not reservator:
        return False
    return Reservation.objects.filter(
        booking_user=reservator,
        store=store,
        booking_status=saved_status,
    ).exists()


def _get_next_ym(year: int, month: int) -> str:
    """
    来月リンク用 YYYY-MM
    """
    if month == 12:
        return f"{year + 1}-01"
    return f"{year}-{month + 1:02d}"


def _get_reservator_initial(customer: CustomerAccount | None) -> dict[str, str]:
    """
    予約モーダルの初期値用：
    - ログイン顧客に紐づく Reservator があればその値
    - なければ CustomerAccount の値（あれば）をベースに返す
    """
    if not customer:
        return {"full_name": "", "full_name_kana": "", "email": "", "phone_number": ""}

    r = Reservator.objects.filter(customer_account=customer).first()
    if r:
        return {
            "full_name": r.full_name or (customer.nickname or ""),
            "full_name_kana": r.full_name_kana or "",
            "email": r.email or (customer.sub_email or customer.email or ""),
            "phone_number": r.phone_number or (customer.phone_number or ""),
        }

    return {
        "full_name": customer.nickname or "",
        "full_name_kana": "",
        "email": (customer.sub_email or customer.email or ""),
        "phone_number": (customer.phone_number or ""),
    }


# =========================
# customer views
# =========================
class customer_mapView(TemplateView):
    template_name = "stores/customer_map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stores"] = Store.objects.prefetch_related('images').all()
        return context


class customer_store_mapView(TemplateView):
    template_name = "stores/customer_store_map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = get_object_or_404(Store, pk=self.kwargs["pk"])
        context["store"] = store

        # ★星評価
        context.update(_get_store_rating_context(store))

        # ★保存判定
        customer = _get_customer_from_user(self.request.user)
        context["is_saved"] = _get_is_saved_for_customer(customer=customer, store=store)

        # ★検索条件（パンくず用）
        context.update({
            "keyword": self.request.GET.get("keyword", ""),
            "area": self.request.GET.get("area", ""),
            "date": self.request.GET.get("date", ""),
            "time": self.request.GET.get("time", ""),
            "sort": self.request.GET.get("sort", ""),
            "from_search": self.request.GET.get("from_search", ""),
        })

        return context


class customer_menu_courseView(TemplateView):
    template_name = "stores/customer_menu_course.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        store = get_object_or_404(Store, pk=self.kwargs["pk"])
        context["store"] = store

        # ★ID209-390 はメニューが無ければ自動生成して “ある扱い” にする（画像も割り当て）
        _ensure_store_menus(store=store, per_store=6, pool_rel="media/_pool/store/food", rotate=True)

        context["menu_items"] = (
            StoreMenu.objects
            .filter(store=store)
            .select_related("store")
            .order_by("id")
        )

        # ★営業時間情報（UIで使う）
        intervals = _get_store_intervals(store)
        closed_ranges = _build_closed_ranges(intervals)
        context["store_intervals_json"] = _format_intervals_for_js(intervals)
        context["closed_ranges_json"] = _format_intervals_for_js(closed_ranges)
        context["has_business_hours"] = bool(intervals)

        # ★ネット予約対応（店舗アカウント or ID209-390）
        context["has_account"] = has_net_reservation(store)

        # ★星評価
        context.update(_get_store_rating_context(store))

        # ★保存判定
        customer = _get_customer_from_user(self.request.user)
        context["is_saved"] = _get_is_saved_for_customer(customer=customer, store=store)

        # ★検索条件（パンくず用）
        context.update({
            "keyword": self.request.GET.get("keyword", ""),
            "area": self.request.GET.get("area", ""),
            "date": self.request.GET.get("date", ""),
            "time": self.request.GET.get("time", ""),
            "sort": self.request.GET.get("sort", ""),
            "from_search": self.request.GET.get("from_search", ""),
        })

        return context


class customer_store_basic_editView(TemplateView):
    template_name = "stores/customer_store_basic_edit.html"


# -----------------------------
# 予約：店舗トップ（顧客）
# -----------------------------
class customer_store_infoView(TemplateView):
    template_name = "stores/customer_store_info.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        store = get_object_or_404(Store.objects.select_related("genre_master", "area", "scene"), pk=self.kwargs["pk"])
        context["store"] = store

        # アクセスログの記録
        StoreAccessLog.objects.create(store=store)

        # 店舗画像
        context["store_images"] = StoreImage.objects.filter(store=store).order_by("id")

        # ★ネット予約対応（店舗アカウント or ID209-390）
        context["has_account"] = has_net_reservation(store)

        # 表示月（?ym=YYYY-MM）
        ym = self.request.GET.get("ym")
        today = timezone.localdate()
        if ym:
            y, m = ym.split("-")
            year, month = int(y), int(m)
        else:
            year, month = today.year, today.month

        # 過去月を見せない（今月に丸め）
        if (year, month) < (today.year, today.month):
            year, month = today.year, today.month

        context["cal_year"] = year
        context["cal_month"] = month

        # ★「来月を見る→」ボタン用
        context["next_ym"] = _get_next_ym(year, month)

        # ★ID209-390なら、その月の予約設定を自動生成（未来日だけ）
        _ensure_month_online_settings(store, year, month)

        start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = date(year, month, last_day)

        # 受付中の日（過去日は除外）※ date型のまま保持
        open_days_dates = list(
            StoreOnlineReservation.objects.filter(
                store=store,
                date__range=(start, end),
                booking_status=True,
            ).values_list("date", flat=True)
        )
        open_days_dates = [d for d in open_days_dates if d >= today]

        # ★テンプレの「今月0件判定」用（文字列）
        context["open_days"] = [d.isoformat() for d in sorted(open_days_dates)]

        # ★カレンダー表示用（当月：6週×7日=42マス）
        open_set = set(open_days_dates)

        first = date(year, month, 1)
        offset = first.weekday()  # 月曜始まり
        grid_start = first - timedelta(days=offset)

        calendar_cells = []
        for i in range(42):
            d = grid_start + timedelta(days=i)
            in_month = (d.month == month and d.year == year)

            if not in_month:
                is_open = False
                is_disabled = True
            else:
                if d < today:
                    is_open = False
                    is_disabled = True
                else:
                    is_open = (d in open_set)
                    is_disabled = (not is_open)

            calendar_cells.append({
                "date": d,
                "iso": d.isoformat(),
                "day": d.day,
                "in_month": in_month,
                "is_open": is_open,
                "is_disabled": is_disabled,
                "weekday": d.weekday(),
            })

        context["calendar_cells"] = calendar_cells
        context["weekdays_ja"] = ["月", "火", "水", "木", "金", "土", "日"]

        # 月送りリンク
        def _ym_str(y: int, m: int) -> str:
            return f"{y}-{m:02d}"

        # 次月
        ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
        context["cal_next_ym"] = _ym_str(ny, nm)

        # 前月（ただし過去月は出さない）
        py, pm = (year - 1, 12) if month == 1 else (year, month - 1)
        prev_ym = _ym_str(py, pm)
        is_prev_allowed = (py, pm) >= (today.year, today.month)
        context["cal_prev_ym"] = prev_ym
        context["cal_prev_allowed"] = is_prev_allowed

        # ログイン顧客（初期値用）
        customer = _get_customer_from_user(self.request.user)
        context["login_customer"] = customer

        # ★予約モーダル初期値
        context["reservator_initial"] = _get_reservator_initial(customer)

        # ★保存判定
        context["is_saved"] = _get_is_saved_for_customer(customer=customer, store=store)

        # JS側で使う
        context["today"] = today
        context["now_hm"] = timezone.localtime().strftime("%H:%M")

        # ★営業時間情報
        intervals = _get_store_intervals(store)
        closed_ranges = _build_closed_ranges(intervals)
        context["store_intervals_json"] = _format_intervals_for_js(intervals)
        context["closed_ranges_json"] = _format_intervals_for_js(closed_ranges)
        context["has_business_hours"] = bool(intervals)

        # ★星評価
        context.update(_get_store_rating_context(store))

        # ★検索条件（パンくず用）
        context.update({
            "keyword": self.request.GET.get("keyword", ""),
            "area": self.request.GET.get("area", ""),
            "date": self.request.GET.get("date", ""),
            "time": self.request.GET.get("time", ""),
            "sort": self.request.GET.get("sort", ""),
            "from_search": self.request.GET.get("from_search", ""),
        })

        return context


# -----------------------------
# 予約：カレンダー受付状況 JSON
# -----------------------------
class StoreAvailabilityJsonView(View):
    def get(self, request, store_id):
        store = get_object_or_404(Store, pk=store_id)

        ym = request.GET.get("ym")
        today = timezone.localdate()
        if ym:
            y, m = ym.split("-")
            year, month = int(y), int(m)
        else:
            year, month = today.year, today.month

        # 過去月を丸める
        if (year, month) < (today.year, today.month):
            year, month = today.year, today.month

        # ★ID209-390なら、その月の予約設定を自動生成（未来日だけ）
        _ensure_month_online_settings(store, year, month)

        start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = date(year, month, last_day)

        open_days = list(
            StoreOnlineReservation.objects.filter(
                store=store,
                date__range=(start, end),
                booking_status=True,
            ).values_list("date", flat=True)
        )
        open_days = [d for d in open_days if d >= today]

        return JsonResponse({
            "year": year,
            "month": month,
            "open_days": [d.isoformat() for d in sorted(open_days)],
        })


# -----------------------------
# ★ 予約：選択可能な時間候補 JSON
# -----------------------------
class StoreTimeSlotsJsonView(View):
    """
    GET /stores/time-slots/<store_id>/?date=YYYY-MM-DD&course_minutes=60
    """
    def get(self, request: HttpRequest, store_id: int):
        store = get_object_or_404(Store, pk=store_id)

        date_s = (request.GET.get("date") or "").strip()
        course_s = (request.GET.get("course_minutes") or "").strip()

        try:
            target_date = date.fromisoformat(date_s)
        except Exception:
            return JsonResponse({"ok": False, "error": "date が不正です。"}, status=400)

        try:
            course_minutes = int(course_s)
        except Exception:
            return JsonResponse({"ok": False, "error": "course_minutes が不正です。"}, status=400)

        if course_minutes not in (30, 60, 90, 120, 150):
            return JsonResponse({"ok": False, "error": "course_minutes が不正です。"}, status=400)

        intervals = _get_store_intervals(store)
        if not intervals:
            return JsonResponse({"ok": True, "slots": [], "reason": "営業時間未設定"})

        # 受付日チェック（ID209-390は未設定なら自動作成）
        setting = StoreOnlineReservation.objects.filter(store=store, date=target_date).first()
        if not setting:
            setting = _ensure_online_setting(store, target_date)

        if not setting or not setting.booking_status:
            return JsonResponse({"ok": True, "slots": [], "reason": "この日は受付していません"})

        step = 15  # 15分刻み

        today = timezone.localdate()
        now_t = timezone.localtime().time()

        slots: list[str] = []
        for itv in intervals:
            start_m = _time_to_minutes(itv.start)
            end_m = _time_to_minutes(itv.end)

            last_start_m = end_m - course_minutes
            if last_start_m < start_m:
                continue

            m = start_m
            while m <= last_start_m:
                t = _minutes_to_time(m)

                # 当日の過去時刻は除外
                if target_date == today and t < now_t:
                    m += step
                    continue

                ok, _, _end_t = _validate_customer_reservation_time(
                    store=store,
                    visit_date=target_date,
                    visit_time=t,
                    course_minutes=course_minutes,
                )
                if ok:
                    slots.append(t.strftime("%H:%M"))

                m += step

        return JsonResponse(
            {
                "ok": True,
                "date": target_date.isoformat(),
                "course_minutes": course_minutes,
                "slots": slots,
                "intervals": _format_intervals_for_js(intervals),
                "closed_ranges": _format_intervals_for_js(_build_closed_ranges(intervals)),
            }
        )


# -----------------------------
# 予約：作成
# -----------------------------
class CustomerReservationCreateView(LoginRequiredMixin, View):
    login_url = "accounts:customer_login"

    def post(self, request, store_id):
        store = get_object_or_404(Store, pk=store_id)
        form = CustomerReserveForm(request.POST)

        if not form.is_valid():
            messages.error(request, "入力内容にエラーがあります。")
            return redirect("stores:customer_store_info", pk=store.id)

        visit_date = form.cleaned_data["visit_date"]
        visit_time = form.cleaned_data["visit_time"]
        visit_count = int(form.cleaned_data["visit_count"])
        course_minutes = int(form.cleaned_data["course_minutes"])

        # 過去・現在時刻チェック
        today = timezone.localdate()
        now = timezone.localtime()

        if visit_date < today:
            messages.error(request, "過去の日付は予約できません。")
            return redirect("stores:customer_store_info", pk=store.id)

        if visit_date == today and visit_time < now.time():
            messages.error(request, "現在時刻より前の時刻は予約できません。")
            return redirect("stores:customer_store_info", pk=store.id)

        # 受付チェック（ID209-390は未設定なら自動作成）
        setting = StoreOnlineReservation.objects.filter(store=store, date=visit_date).first()
        if not setting:
            setting = _ensure_online_setting(store, visit_date)

        if not setting or not setting.booking_status:
            messages.error(request, "この日はネット予約を受け付けていません。")
            return redirect("stores:customer_store_info", pk=store.id)

        # ★営業時間チェック
        ok, reason, end_time = _validate_customer_reservation_time(
            store=store,
            visit_date=visit_date,
            visit_time=visit_time,
            course_minutes=course_minutes,
        )

        if not ok or end_time is None:
            messages.error(request, reason or "営業時間チェックに失敗しました。")
            return redirect("stores:customer_store_info", pk=store.id)

        # 席数チェック（日単位合計）
        used = (
            Reservation.objects
            .filter(store=store, visit_date=visit_date)
            .aggregate(models.Sum("visit_count"))["visit_count__sum"] or 0
        )
        if setting.available_seats and used + visit_count > setting.available_seats:
            messages.error(request, "空席が不足しています。人数を減らすか別日をご選択ください。")
            return redirect("stores:customer_store_info", pk=store.id)

        # コース名
        course_name = _course_name(course_minutes)

        # 予約者（Reservator）
        customer = _get_customer_from_user(request.user)
        reservator = None

        if customer:
            reservator = Reservator.objects.filter(customer_account=customer).first()

            if reservator is None:
                full_name = form.cleaned_data.get("full_name") or (customer.nickname or "")
                full_name_kana = form.cleaned_data.get("full_name_kana") or ""
                email = form.cleaned_data.get("email") or (customer.sub_email or customer.email or "")
                phone = form.cleaned_data.get("phone_number") or (customer.phone_number or "")

                if not full_name or not email or not phone:
                    messages.error(request, "予約者情報（氏名/メール/電話）が不足しています。")
                    return redirect("stores:customer_store_info", pk=store.id)

                reservator = Reservator.objects.create(
                    customer_account=customer,
                    full_name=full_name,
                    full_name_kana=full_name_kana,
                    email=email,
                    phone_number=phone,
                )
            else:
                changed = False
                if not reservator.full_name and form.cleaned_data.get("full_name"):
                    reservator.full_name = form.cleaned_data["full_name"]
                    changed = True
                if not reservator.full_name_kana and form.cleaned_data.get("full_name_kana"):
                    reservator.full_name_kana = form.cleaned_data["full_name_kana"]
                    changed = True
                if not reservator.email and form.cleaned_data.get("email"):
                    reservator.email = form.cleaned_data["email"]
                    changed = True
                if not reservator.phone_number and form.cleaned_data.get("phone_number"):
                    reservator.phone_number = form.cleaned_data["phone_number"]
                    changed = True
                if changed:
                    reservator.save()
        else:
            required = ["full_name", "full_name_kana", "email", "phone_number"]
            for f in required:
                if not form.cleaned_data.get(f):
                    messages.error(request, "予約者情報（氏名/かな/電話/メール）は必須です。")
                    return redirect("stores:customer_store_info", pk=store.id)

            reservator = Reservator.objects.create(
                customer_account=None,
                full_name=form.cleaned_data["full_name"],
                full_name_kana=form.cleaned_data["full_name_kana"],
                email=form.cleaned_data["email"],
                phone_number=form.cleaned_data["phone_number"],
            )

        # 予約ステータス
        status = ReservationStatus.objects.get_or_create(status="予約確定")[0]

        reservation = Reservation.objects.create(
            booking_user=reservator,
            store=store,
            visit_date=visit_date,
            visit_time=visit_time,
            start_time=visit_time,
            end_time=end_time,
            visit_count=visit_count,
            course=course_name,
            booking_status=status,
        )

        return redirect("stores:customer_reservation_complete", reservation_id=reservation.id)


class customer_reservation_completeView(LoginRequiredMixin, TemplateView):
    template_name = "stores/customer_reservation_complete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reservation = get_object_or_404(Reservation, pk=self.kwargs["reservation_id"])
        
        # 予約者がログインユーザー本人、または予約者のメールアドレスが一致するか等の簡易チェック（セキュリティ）
        customer = _get_customer_from_user(self.request.user)
        if reservation.booking_user.customer_account != customer:
            # 他人の予約は見せない
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        context["reservation"] = reservation
        return context


class customer_store_new_registerView(LoginRequiredMixin, TemplateView):
    template_name = "stores/customer_store_new_register.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial_data = self.request.session.get("store_register_data", {})
        context["form"] = StoreRegistrationForm(initial=initial_data)
        return context

    def post(self, request, *args, **kwargs):
        form = StoreRegistrationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            serializable_data = {}
            for key, value in data.items():
                if isinstance(value, models.Model):
                    serializable_data[key] = value.pk
                elif hasattr(value, "isoformat"):
                    serializable_data[key] = value.isoformat()
                else:
                    serializable_data[key] = value

            request.session["store_register_data"] = serializable_data
            return redirect("stores:customer_store_new_register_confirm")

        return render(request, self.template_name, {"form": form})


class customer_store_new_register_confirmView(LoginRequiredMixin, TemplateView):
    template_name = "stores/customer_store_new_register_confirm.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = self.request.session.get("store_register_data")
        if not data:
            return redirect("stores:customer_store_new_register")

        display_data = data.copy()
        if "area" in data:
            display_data["area_obj"] = get_object_or_404(Area, pk=data["area"])
        if "scene" in data:
            display_data["scene_obj"] = get_object_or_404(Scene, pk=data["scene"])
        if "genre_master" in data:
            display_data["genre_master_obj"] = get_object_or_404(Genre, pk=data["genre_master"])

        context["data"] = display_data
        return context

    def post(self, request, *args, **kwargs):
        if "back" in request.POST:
            return redirect("stores:customer_store_new_register")

        data = request.session.get("store_register_data")
        if not data:
            messages.error(request, "セッションがタイムアウトしました。最初からやり直してください。")
            return redirect("stores:customer_store_new_register")

        form = StoreRegistrationForm(data)
        if form.is_valid():
            store = form.save(commit=False)
            store.creator = _get_customer_from_user(request.user)

            # 住所から座標を自動取得
            if store.address:
                try:
                    url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={urllib.parse.quote(store.address)}"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        geo_data = response.json()
                        if geo_data and len(geo_data) > 0:
                            coords = geo_data[0]['geometry']['coordinates']
                            store.longitude = coords[0]
                            store.latitude = coords[1]
                except Exception as e:
                    print(f"Geocoding error: {e}")
            
            store.save()

            if "store_register_data" in request.session:
                del request.session["store_register_data"]

            return redirect("stores:customer_store_new_register_complete")

        messages.error(request, "登録に失敗しました。")
        return redirect("stores:customer_store_new_register")


class customer_store_new_register_completeView(LoginRequiredMixin, TemplateView):
    template_name = "stores/customer_store_new_register_complete.html"


# =========================
# company views
# =========================
class company_store_infoView(UpdateView):
    model = Store
    form_class = CompanyStoreEditForm
    template_name = "stores/company_store_info.html"
    context_object_name = "store"

    def get_success_url(self):
        messages.success(self.request, "店舗情報を更新しました。")
        return reverse("stores:company_store_info", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        store = form.save(commit=False)
        # 住所が変更された場合、または座標が未設定の場合に再取得
        if "address" in form.changed_data or not store.latitude:
            if store.address:
                try:
                    url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={urllib.parse.quote(store.address)}"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        geo_data = response.json()
                        if geo_data and len(geo_data) > 0:
                            coords = geo_data[0]['geometry']['coordinates']
                            store.longitude = coords[0]
                            store.latitude = coords[1]
                except Exception as e:
                    print(f"Geocoding error: {e}")
        
        store.save()
        return super().form_valid(form)


class company_store_managementView(TemplateView):
    template_name = "stores/company_store_management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query = self.request.GET.get("q", "").strip()
        if query:
            stores_all = Store.objects.filter(Q(store_name__icontains=query)).order_by("store_name")
        else:
            stores_all = Store.objects.all().order_by("store_name")

        # ✅ ページネーション追加 (1ページ 10件)
        from django.core.paginator import Paginator
        page = self.request.GET.get("page") or 1
        paginator = Paginator(stores_all, 10)
        stores_page = paginator.get_page(page)

        context["stores"] = stores_page
        context["query"] = query
        return context


# =========================
# store views（店舗側）
# =========================
class store_basic_editView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "stores/store_basic_edit.html"
    login_url = "accounts:store_login"

    def test_func(self):
        return is_store_user(self.request.user)

    def get(self, request, *args, **kwargs):
        store = get_store_from_user(request.user)
        if store is None:
            messages.error(request, "店舗アカウントに紐づく店舗が見つかりません。")
            return redirect(self.login_url)

        form = StoreBasicForm(instance=store)
        image_formset = StoreImageFormSet(instance=store, prefix="images")
        menu_formset = StoreMenuFormSet(instance=store, prefix="menus")

        context = {
            "store": store,
            "form": form,
            "image_formset": image_formset,
            "menu_formset": menu_formset,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        store = get_store_from_user(request.user)
        if store is None:
            messages.error(request, "店舗アカウントに紐づく店舗が見つかりません。")
            return redirect(self.login_url)

        form = StoreBasicForm(request.POST, instance=store)

        image_formset = StoreImageFormSet(
            request.POST,
            request.FILES,
            instance=store,
            prefix="images",
        )
        menu_formset = StoreMenuFormSet(
            request.POST,
            request.FILES,
            instance=store,
            prefix="menus",
        )

        if form.is_valid() and image_formset.is_valid() and menu_formset.is_valid():
            form.save()

            image_objs = image_formset.save(commit=False)
            for obj in image_objs:
                if not getattr(obj, "image_path", ""):
                    obj.image_path = "----"
                obj.store = store
                obj.save()
            for obj in image_formset.deleted_objects:
                obj.delete()

            menu_objs = menu_formset.save(commit=False)
            for obj in menu_objs:
                if not getattr(obj, "image_path", ""):
                    obj.image_path = "----"
                obj.store = store
                obj.save()
            for obj in menu_formset.deleted_objects:
                obj.delete()

            messages.success(request, "店舗情報・店舗画像・メニューを保存しました。")
            return redirect(reverse("stores:store_basic_edit"))

        messages.error(request, "入力内容にエラーがあります。")

        print("FORM ERRORS:", form.errors)
        print("IMAGE NON_FORM_ERRORS:", image_formset.non_form_errors())
        print("MENU NON_FORM_ERRORS:", menu_formset.non_form_errors())
        print("IMAGE ERRORS:", image_formset.errors)
        print("MENU ERRORS:", menu_formset.errors)
        print("FILES:", request.FILES)
        print("POST keys:", list(request.POST.keys())[:30])

        context = {
            "store": store,
            "form": form,
            "image_formset": image_formset,
            "menu_formset": menu_formset,
        }
        return render(request, self.template_name, context)


class store_topView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "stores/store_top.html"
    login_url = "accounts:store_login"

    def test_func(self):
        return is_store_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        store_account = self.request.user.storeaccount
        store = store_account.store
        context["store"] = store

        # --- アクセス数チャート用データの集計 (過去7日間) ---
        today = timezone.now().date()
        date_list = [today - timedelta(days=i) for i in range(6, -1, -1)]

        access_counts = []
        labels = []
        for d in date_list:
            count = StoreAccessLog.objects.filter(
                store=store,
                accessed_at__date=d
            ).count()
            access_counts.append(count)
            labels.append(d.strftime("%Y-%m-%d"))

        context["chart_labels"] = labels
        context["chart_data"] = access_counts
        print(f"DEBUG: Store={store.store_name}, Labels={labels}, Data={access_counts}")

        today = timezone.localdate()

        today_setting = StoreOnlineReservation.objects.filter(store=store, date=today).first()
        if today_setting is not None:
            context["is_online_open"] = bool(today_setting.booking_status)
            context["today_available_seats"] = int(today_setting.available_seats or 0)
        else:
            context["is_online_open"] = False
            context["today_available_seats"] = 0

        today_qs = (
            Reservation.objects
            .filter(store=store, visit_date=today)
            .select_related("booking_user")
            .order_by("start_time", "visit_time")
        )
        context["today_reservations"] = today_qs
        context["today_reservations_count"] = today_qs.count()

        month_start = today.replace(day=1)
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1, day=1)

        context["month_reservations_count"] = (
            Reservation.objects.filter(
                store=store,
                visit_date__gte=month_start,
                visit_date__lt=next_month_start
            ).count()
        )

        return context


class store_logoutView(TemplateView):
    template_name = "accounts/store_logout.html"


# =========================
# misc
# =========================
def store_delete_execute(request, pk):
    store = get_object_or_404(Store, pk=pk)
    name = store.store_name
    store.delete()

    msg = f"店舗「{name}」の削除"
    encoded_msg = urllib.parse.quote(msg)
    return redirect(reverse("commons:company_common_complete") + f"?message={encoded_msg}")


# =========================
# 顧客：店舗写真アップロード
# =========================
class customer_store_photo_uploadView(LoginRequiredMixin, View):
    """
    ログイン中の顧客が店舗に写真を投稿する
    """
    login_url = "/accounts/customer_login/"
    
    def post(self, request, pk):
        store = get_object_or_404(Store, pk=pk)
        
        # アップロードされた画像を取得
        uploaded_file = request.FILES.get("photo")
        if not uploaded_file:
            messages.error(request, "画像ファイルを選択してください。")
            return redirect("stores:customer_store_info", pk=pk)
        
        # ImageStatus の取得（デフォルトは「公開」など）
        from commons.models import ImageStatus
        default_status = ImageStatus.objects.filter(status="公開").first()
        if not default_status:
            default_status = ImageStatus.objects.first()
        
        if not default_status:
            messages.error(request, "画像ステータスが設定されていません。管理者に連絡してください。")
            return redirect("stores:customer_store_info", pk=pk)
        
        # StoreImage を作成
        store_image = StoreImage(
            store=store,
            image_file=uploaded_file,
            image_status=default_status,
            uploaded_by=request.user,
        )
        store_image.save()
        
        messages.success(request, "写真を投稿しました！")
        return redirect("stores:customer_store_photos", pk=pk)


# =========================
# 顧客：店舗写真タブ
# =========================
class customer_store_photosView(TemplateView):
    """
    店舗の写真タブ - 写真の一覧表示と投稿
    """
    template_name = "stores/customer_store_photos.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = get_object_or_404(Store.objects.select_related("genre_master", "area", "scene"), pk=self.kwargs["pk"])
        context["store"] = store
        
        # 店舗画像一覧
        context["store_images"] = StoreImage.objects.filter(store=store).select_related("uploaded_by").order_by("-id")
        
        # 共通コンテキスト
        customer = _get_customer_from_user(self.request.user)
        context["is_saved"] = _get_is_saved_for_customer(customer=customer, store=store)
        context.update(_get_store_rating_context(store))
        
        # 検索条件（パンくず用）
        context.update({
            "keyword": self.request.GET.get("keyword", ""),
            "area": self.request.GET.get("area", ""),
            "date": self.request.GET.get("date", ""),
            "time": self.request.GET.get("time", ""),
            "sort": self.request.GET.get("sort", ""),
            "from_search": self.request.GET.get("from_search", ""),
        })
        
        return context
