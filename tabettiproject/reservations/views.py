from __future__ import annotations

from datetime import date, time

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpRequest, HttpResponse,JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.shortcuts import render
from django.views.generic import TemplateView
from django.utils import timezone
from datetime import timedelta, datetime
from dataclasses import dataclass

from commons.models import CustomerAccount, Reservation, ReservationStatus, StoreOnlineReservation, Store


# ----------------------------
# 共通ヘルパ
# ----------------------------
def _get_customer_user(request: HttpRequest) -> CustomerAccount:
    if not request.user.is_authenticated:
        raise Http404("ログインしてください。")

    # すでにCustomerAccountならそのまま返す
    if isinstance(request.user, CustomerAccount):
        return request.user

    # Accountとしてログインしていても、同じpkのCustomerAccountがあれば顧客扱いにする
    try:
        return CustomerAccount.objects.get(pk=request.user.pk)
    except CustomerAccount.DoesNotExist:
        raise Http404("顧客アカウントではありません。")


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
from django.db.models import Prefetch

class store_reservation_historyView(LoginRequiredMixin, TemplateView):
    template_name = "reservations/store_reservation_history.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = _get_customer_user(self.request)

        reservations = (
            Reservation.objects
            .select_related("store", "booking_user", "booking_status")
            .prefetch_related("store__images")  # 追加
            .filter(booking_user__customer_account=customer)
            .order_by("-visit_date", "-visit_time", "-id")
        )

        ctx["reservations"] = reservations
        return ctx


class store_reservation_confirmView(LoginRequiredMixin, TemplateView):
    template_name = "reservations/store_reservation_confirm.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        customer = _get_customer_user(self.request)

        reservation_id = int(kwargs.get("reservation_id"))
        reservation = _get_customer_reservation(customer, reservation_id)

        store_page_url = _get_store_page_url(reservation.store_id)

        # ----------------------------
        # 3日前ルール（"日付単位"で判定）
        # 来店日の3日前(0:00)になったら変更・キャンセル不可
        # 例）来店日 1/28 → 1/25 になった瞬間から不可
        # ----------------------------
        today = timezone.localdate()  # ローカル日付（JST想定）
        limit_date = reservation.visit_date - timedelta(days=3)
        can_modify = today < limit_date

        ctx.update(
            {
                "reservation": reservation,
                "store": reservation.store,
                "store_page_url": store_page_url,
                "can_modify": can_modify,  # テンプレの disabled 判定用
                "limit_date": limit_date,  # （表示したい時用：不要なら消してOK）
            }
        )
        return ctx

# ----------------------------
# 予約変更（GET/POST）   
# ----------------------------
class store_reservation_editView(LoginRequiredMixin, View):
    template_name = "reservations/store_reservation_edit.html"

    # ----------------------------
    # 3日前ルール（元予約の編集可否）
    # ----------------------------
    def _can_modify(self, reservation: Reservation) -> bool:
        """
        来店日の3日前(0:00)になったら変更不可（＝日付単位）
        例）来店日 1/28 → 1/25 になった瞬間から不可
        """
        today = timezone.localdate()
        limit_date = reservation.visit_date - timedelta(days=3)
        return today < limit_date

    # ----------------------------
    # 変更先の最短日（今日+4日）
    # ----------------------------
    def _min_editable_date(self) -> date:
        return timezone.localdate() + timedelta(days=4)

    # ----------------------------
    # 受付中チェック（B仕様：未設定日もNG）
    # ----------------------------
    def _is_store_accepting_on(self, store_id: int, target_date: date) -> bool:
        row = StoreOnlineReservation.objects.filter(store_id=store_id, date=target_date).first()
        if row is None:
            return False  # ★B仕様：未設定日は受付停止扱い
        return bool(row.booking_status)

    # ----------------------------
    # 営業時間ヘルパ（Store.open/close 1・2枠）
    # ----------------------------
    @dataclass(frozen=True)
    class TimeInterval:
        start: time
        end: time

    def _time_to_minutes(self, t: time) -> int:
        return t.hour * 60 + t.minute

    def _minutes_to_time(self, m: int) -> time:
        m = max(0, min(24 * 60 - 1, m))
        return time(m // 60, m % 60)

    def _get_store_intervals(self, store) -> list["store_reservation_editView.TimeInterval"]:
        """
        Store の open/close から営業時間区間を返す（最大2区間）
        - start>=end は無効として捨てる
        """
        intervals: list[store_reservation_editView.TimeInterval] = []

        def push(a: time | None, b: time | None) -> None:
            if isinstance(a, time) and isinstance(b, time) and self._time_to_minutes(b) > self._time_to_minutes(a):
                intervals.append(self.TimeInterval(a, b))

        push(store.open_time_1, store.close_time_1)
        push(store.open_time_2, store.close_time_2)

        intervals.sort(key=lambda x: self._time_to_minutes(x.start))
        return intervals

    def _is_inside_one_interval(
        self,
        start: time,
        end: time,
        intervals: list["store_reservation_editView.TimeInterval"],
    ) -> bool:
        """
        予約の開始〜終了が「どれか1つの営業時間区間」に完全に収まるか
        中休みをまたぐのはNG
        """
        s = self._time_to_minutes(start)
        e = self._time_to_minutes(end)
        if e <= s:  # 日跨ぎ/逆転NG
            return False

        for itv in intervals:
            a = self._time_to_minutes(itv.start)
            b = self._time_to_minutes(itv.end)
            # ★閉店ぴったりOK → e <= b
            if a <= s and e <= b:
                return True
        return False

    # ----------------------------
    # 15分刻み：開始候補生成（コース込みで営業時間判定）
    # ----------------------------
    def _build_available_start_times(
        self,
        *,
        store,
        target_date: date,
        course_minutes: int,
        step_min: int = 15,
    ) -> list[str]:
        # ★変更先の最短日チェック（今日+4日未満なら候補なし）
        if target_date < self._min_editable_date():
            return []

        intervals = self._get_store_intervals(store)
        if not intervals:
            return []

        # B仕様：その日が受付中でなければ候補なし
        if not self._is_store_accepting_on(store.id, target_date):
            return []

        starts: list[str] = []

        for itv in intervals:
            a = self._time_to_minutes(itv.start)
            b = self._time_to_minutes(itv.end)

            last_start = b - course_minutes
            t = a
            while t <= last_start:
                st = self._minutes_to_time(t)
                ed = self._minutes_to_time(t + course_minutes)

                # 中休み跨ぎ/営業時間外NG（「どれか1枠」に完全に収まること）
                if self._is_inside_one_interval(st, ed, intervals):
                    starts.append(f"{st.hour:02d}:{st.minute:02d}")

                t += step_min

        # 重複除去＋ソート
        starts = sorted(set(starts), key=lambda s: int(s[:2]) * 60 + int(s[3:]))
        return starts

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        customer = _get_customer_user(request)

        reservation_id = int(kwargs.get("reservation_id"))
        reservation = _get_customer_reservation(customer, reservation_id)

        store_page_url = _get_store_page_url(reservation.store_id)
        can_modify = self._can_modify(reservation)

        # ★変更先の最短日（今日+4日）をテンプレへ
        min_date_str = self._min_editable_date().isoformat()

        # コース文字列 → minutes（固定）
        minutes_map = {
            "30分コース": 30,
            "1時間コース": 60,
            "1時間30分コース": 90,
            "2時間コース": 120,
            "2時間30分コース": 150,
        }
        current_minutes = minutes_map.get(reservation.course, 60)

        available_start_times = self._build_available_start_times(
            store=reservation.store,
            target_date=reservation.visit_date,
            course_minutes=current_minutes,
            step_min=15,
        )

        ctx = {
            "reservation": reservation,
            "store": reservation.store,
            "store_page_url": store_page_url,
            "can_modify": can_modify,
            "min_date_str": min_date_str,  # ★HTMLのmin用
            # ★B対応：時刻候補（15分刻みで「選べる開始時刻だけ」）
            "available_start_times": available_start_times,
            # ★テンプレ側でコース選択の初期値に使う（必要なら）
            "current_course_minutes": current_minutes,
        }
        return render(request, self.template_name, ctx)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        customer = _get_customer_user(request)
        reservation_id = int(kwargs.get("reservation_id"))
        reservation = _get_customer_reservation(customer, reservation_id)

        # ★ 3日前ルール：POSTでも必ず弾く
        if not self._can_modify(reservation):
            messages.error(request, "来店日の3日前以降は変更できません。")
            return redirect("reservations:store_reservation_confirm", reservation_id=reservation.id)

        visit_date_s = (request.POST.get("visit_date") or "").strip()
        visit_time_s = (request.POST.get("visit_time") or "").strip()
        visit_count_s = (request.POST.get("visit_count") or "").strip()
        course_minutes_s = (request.POST.get("course_minutes") or "").strip()

        errors: list[str] = []

        # visit_date
        try:
            new_date = date.fromisoformat(visit_date_s)
        except Exception:
            errors.append("来店日が不正です。")
            new_date = reservation.visit_date

        # ★変更先の最短日（今日+4日）チェック
        if new_date < self._min_editable_date():
            messages.error(request, "その日時は選択できません。")
            return redirect("reservations:store_reservation_edit", reservation_id=reservation.id)

        # visit_time（select でも input でも "HH:MM" で来る）
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

        # course_minutes -> course(文字列)
        course_map = {
            30: "30分コース",
            60: "1時間コース",
            90: "1時間30分コース",
            120: "2時間コース",
            150: "2時間30分コース",
        }
        try:
            new_minutes = int(course_minutes_s)
            new_course = course_map[new_minutes]
        except Exception:
            errors.append("コースが不正です。")
            new_minutes = None  # type: ignore[assignment]
            new_course = reservation.course

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect("reservations:store_reservation_edit", reservation_id=reservation.id)

        # ----------------------------
        # ★受付中 + 営業時間 + 中休み跨ぎチェック
        # ----------------------------
        if not self._is_store_accepting_on(reservation.store_id, new_date):
            messages.error(request, "その日時は選択できません。")
            return redirect("reservations:store_reservation_edit", reservation_id=reservation.id)

        # コース分から終了時刻を算出して判定
        try:
            end_dt = datetime.combine(new_date, new_time) + timedelta(minutes=int(new_minutes))  # type: ignore[arg-type]
        except Exception:
            messages.error(request, "その日時は選択できません。")
            return redirect("reservations:store_reservation_edit", reservation_id=reservation.id)

        # 日跨ぎNG
        if end_dt.date() != new_date:
            messages.error(request, "その日時は選択できません。")
            return redirect("reservations:store_reservation_edit", reservation_id=reservation.id)

        new_end = end_dt.time()

        intervals = self._get_store_intervals(reservation.store)
        if not intervals:
            messages.error(request, "その日時は選択できません。")
            return redirect("reservations:store_reservation_edit", reservation_id=reservation.id)

        if not self._is_inside_one_interval(new_time, new_end, intervals):
            messages.error(request, "その日時は選択できません。")
            return redirect("reservations:store_reservation_edit", reservation_id=reservation.id)

        # ----------------------------
        # 保存
        # ----------------------------
        reservation.visit_date = new_date
        reservation.visit_time = new_time
        reservation.start_time = new_time
        reservation.end_time = new_end
        reservation.visit_count = new_count
        reservation.course = new_course
        reservation.save()

        messages.success(request, "ご予約内容を変更しました。")
        return redirect("reservations:store_reservation_confirm", reservation_id=reservation.id)


class available_timesView(LoginRequiredMixin, View):
    """
    来店日 + コース分 から、選択可能な開始時刻（15分刻み）を返すAPI
    - 未設定日（StoreOnlineReservationなし） -> NG（times=[]）
    - booking_status=False -> NG
    - 変更先が今日+4日未満 -> NG
    - 営業時間外 / 中休み跨ぎ -> 候補に出さない
    """
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        customer = _get_customer_user(request)

        reservation_id = int(kwargs.get("reservation_id"))
        reservation = _get_customer_reservation(customer, reservation_id)
        store = reservation.store

        date_s = (request.GET.get("date") or "").strip()
        course_s = (request.GET.get("course_minutes") or "").strip()

        try:
            target_date = date.fromisoformat(date_s)
            course_minutes = int(course_s)
        except Exception:
            return JsonResponse({"times": []})

        if course_minutes not in (30, 60, 90, 120, 150):
            return JsonResponse({"times": []})

        helper = store_reservation_editView()

        # ★変更先が今日+4日未満なら候補なし
        if target_date < helper._min_editable_date():
            return JsonResponse({"times": []})

        times = helper._build_available_start_times(
            store=store,
            target_date=target_date,
            course_minutes=course_minutes,
            step_min=15,
        )
        return JsonResponse({"times": times})

# ----------------------------
# 予約キャンセル（GET/POST）
# ----------------------------
class store_reservation_cancelView(LoginRequiredMixin, TemplateView):
    template_name = "reservations/store_reservation_cancel.html"

    @staticmethod
    def _can_modify(reservation: Reservation) -> bool:
        """
        来店日時の3日前より前なら True（変更・キャンセル可）
        来店日時の3日前になった瞬間から False（変更・キャンセル不可）
        """
        # Djangoのtimezoneを使う（from django.utils import timezone が必要）
        visit_dt_naive = datetime.combine(reservation.visit_date, reservation.visit_time)
        tz = timezone.get_current_timezone()
        visit_dt = timezone.make_aware(visit_dt_naive, tz)

        limit_dt = visit_dt - timedelta(days=3)
        return timezone.now() < limit_dt

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = _get_customer_user(self.request)

        reservation_id = int(kwargs.get("reservation_id"))
        reservation = _get_customer_reservation(customer, reservation_id)

        store_page_url = _get_store_page_url(reservation.store_id)

        can_modify = self._can_modify(reservation)

        ctx.update(
            {
                "reservation": reservation,
                "store": reservation.store,
                "store_page_url": store_page_url,
                "can_modify": can_modify,  # ★テンプレでボタンdisabledに使う
            }
        )
        return ctx

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        customer = _get_customer_user(request)
        reservation_id = int(kwargs.get("reservation_id"))
        reservation = _get_customer_reservation(customer, reservation_id)

        # ★ 3日前ルール：POSTでも必ず弾く（URL直叩き対策）
        if not self._can_modify(reservation):
            # メッセージ出したくない → そのまま確認画面へ戻すだけ
            return redirect("reservations:store_reservation_confirm", reservation_id=reservation.id)

        cancel_reason = (request.POST.get("cancel_reason") or "").strip()
        cancel_detail = (request.POST.get("cancel_detail") or "").strip()

        # select の「選択してください」は value="" にしてる前提（テンプレ側）
        if not cancel_reason:
            # ここもメッセージ不要ならconfirmへ戻すだけでもOK
            messages.error(request, "キャンセル理由を選択してください。")
            return redirect("reservations:store_reservation_cancel", reservation_id=reservation.id)

        # cancel_reason フィールドは TextField なのでまとめて保存する
        if cancel_detail:
            reservation.cancel_reason = f"{cancel_reason}\n\n{cancel_detail}"
        else:
            reservation.cancel_reason = cancel_reason

        try:
            _set_reservation_status_cancelled(reservation)
        except Exception:
            # ここも「だるい」ならメッセージ無しで戻すだけでもOK
            messages.error(request, "ステータス更新に失敗しました。")
            return redirect("reservations:store_reservation_cancel", reservation_id=reservation.id)

        reservation.save()
        # 成功は一応残す（いらなければ消してOK）
        messages.success(request, "予約をキャンセルしました。")
        return redirect("reservations:store_reservation_confirm", reservation_id=reservation.id)