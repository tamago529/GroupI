from __future__ import annotations

import urllib.parse

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic.base import TemplateView
from datetime import date, datetime, timedelta
import calendar
from django.http import JsonResponse
from django.db import models


from commons.models import (
    Reservation,
    Store,
    StoreAccount,
    StoreImage,
    StoreMenu,
    StoreOnlineReservation,
    Reservator,
    ReservationStatus, 
    CustomerAccount,
)

from .form import StoreBasicForm, StoreImageFormSet, StoreMenuFormSet, CustomerReserveForm


# =========================
# helper
# =========================
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


# =========================
# customer views
# =========================
class customer_mapView(TemplateView):
    template_name = "stores/customer_map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stores"] = Store.objects.all()
        return context


class customer_menu_courseView(TemplateView):
    template_name = "stores/customer_menu_course.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        store = get_object_or_404(Store, pk=self.kwargs["pk"])
        context["store"] = store

        # ★ この店舗のメニュー一覧（表示順を安定させる）
        context["menu_items"] = (
            StoreMenu.objects
            .filter(store=store)
            .select_related("store")
            .order_by("id")
        )

        return context


class customer_store_basic_editView(TemplateView):
    template_name = "stores/customer_store_basic_edit.html"


# -----------------------------
# 予約：店舗トップ（顧客） ここがメイン
# -----------------------------
import calendar
from datetime import date, datetime, timedelta

from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages

from commons.models import (
    Store,
    StoreImage,
    StoreOnlineReservation,
    Reservation,
    Reservator,
    CustomerAccount,
    ReservationStatus,
)
from .form import CustomerReserveForm


class customer_store_infoView(TemplateView):
    template_name = "stores/customer_store_info.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        store = get_object_or_404(Store, pk=self.kwargs["pk"])
        context["store"] = store

        # 店舗画像（最大5枚などはHTML側で制御）
        context["store_images"] = StoreImage.objects.filter(store=store).order_by("id")

        # 表示月（?ym=YYYY-MM）
        ym = self.request.GET.get("ym")
        today = timezone.localdate()
        if ym:
            y, m = ym.split("-")
            year, month = int(y), int(m)
        else:
            year, month = today.year, today.month

        # ★ 過去月を見せたくない（表示月が今日より前なら今月に丸める）
        if (year, month) < (today.year, today.month):
            year, month = today.year, today.month

        context["cal_year"] = year
        context["cal_month"] = month

        start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = date(year, month, last_day)

        # 受付中の日だけ（○を付ける）
        # ★ 過去日（昨日以前）は open_days から除外して、UIにも○が出ないようにする
        open_days = list(
            StoreOnlineReservation.objects.filter(
                store=store,
                date__range=(start, end),
                booking_status=True,
            ).values_list("date", flat=True)
        )
        open_days = [d for d in open_days if d >= today]
        context["open_days"] = [d.isoformat() for d in sorted(open_days)]

        # ログイン顧客なら初期値用に渡す（CustomerAccountである場合のみ）
        user = self.request.user
        context["login_customer"] = user if (user.is_authenticated and isinstance(user, CustomerAccount)) else None

        # ★ JS 側で「今日」「いま」を使う
        context["today"] = today
        context["now_hm"] = timezone.localtime().strftime("%H:%M")

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

        # ★ 過去月の要求は今月に丸める（触れないようにする）
        if (year, month) < (today.year, today.month):
            year, month = today.year, today.month

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

        # ★ 過去日（昨日以前）は返さない（UIで○が出ない）
        open_days = [d for d in open_days if d >= today]

        return JsonResponse({
            "year": year,
            "month": month,
            "open_days": [d.isoformat() for d in sorted(open_days)],
        })


# -----------------------------
# 予約：作成（Reservator/Reservation を作る）
# -----------------------------
class CustomerReservationCreateView(View):
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

        # -------------------------
        # ★ ここが今回の追加（サーバ側で確実に弾く）
        # -------------------------
        today = timezone.localdate()
        now = timezone.localtime()

        # 1) 昨日以前は予約不可
        if visit_date < today:
            messages.error(request, "過去の日付は予約できません。")
            return redirect("stores:customer_store_info", pk=store.id)

        # 2) 今日で現在時刻未満は予約不可
        if visit_date == today and visit_time < now.time():
            messages.error(request, "現在時刻より前の時刻は予約できません。")
            return redirect("stores:customer_store_info", pk=store.id)

        # -------------------------
        # 受付チェック（その日の受付設定があるか＆受付中か）
        # -------------------------
        setting = StoreOnlineReservation.objects.filter(store=store, date=visit_date).first()
        if not setting or not setting.booking_status:
            messages.error(request, "この日はネット予約を受け付けていません。")
            return redirect("stores:customer_store_info", pk=store.id)

        # -------------------------
        # 席数チェック（簡易：日単位で人数合計）
        # -------------------------
        used = (
            Reservation.objects
            .filter(store=store, visit_date=visit_date)
            .aggregate(models.Sum("visit_count"))["visit_count__sum"] or 0
        )
        if setting.available_seats and used + visit_count > setting.available_seats:
            messages.error(request, "空席が不足しています。人数を減らすか別日をご選択ください。")
            return redirect("stores:customer_store_info", pk=store.id)

        # -------------------------
        # コース名（Reservation.course は CharField）
        # -------------------------
        course_name = "1時間コース" if course_minutes == 60 else "2時間コース"

        # start/end を計算
        start_dt = datetime.combine(visit_date, visit_time)
        end_dt = start_dt + timedelta(minutes=course_minutes)

        # ★ 念のため：終了が日付をまたぐなら弾く（要件次第だが事故防止）
        if end_dt.date() != visit_date:
            messages.error(request, "営業時間外の予約はできません（終了時刻が翌日になります）。")
            return redirect("stores:customer_store_info", pk=store.id)

        # -------------------------
        # 予約者（Reservator）を決める
        # -------------------------
        user = request.user
        reservator = None

        if user.is_authenticated and isinstance(user, CustomerAccount):
            # CustomerAccountに紐づくReservatorがあれば再利用
            reservator = Reservator.objects.filter(customer_account=user).first()

            if reservator is None:
                full_name = form.cleaned_data.get("full_name") or user.nickname
                full_name_kana = form.cleaned_data.get("full_name_kana") or ""
                email = form.cleaned_data.get("email") or user.sub_email
                phone = form.cleaned_data.get("phone_number") or user.phone_number

                if not full_name or not email or not phone:
                    messages.error(request, "予約者情報（氏名/メール/電話）が不足しています。")
                    return redirect("stores:customer_store_info", pk=store.id)

                reservator = Reservator.objects.create(
                    customer_account=user,
                    full_name=full_name,
                    full_name_kana=full_name_kana,
                    email=email,
                    phone_number=phone,
                )
            else:
                # 既存がある場合：空欄だけ補完（必要なら上書きに変更可）
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
            # 未ログイン or CustomerAccount以外 → 予約者情報は全部必須
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

        # -------------------------
        # 予約ステータス（マスタが無ければ作る）
        # -------------------------
        status = ReservationStatus.objects.get_or_create(status="予約確定")[0]

        Reservation.objects.create(
            booking_user=reservator,
            store=store,
            visit_date=visit_date,
            visit_time=visit_time,
            start_time=visit_time,
            end_time=end_dt.time(),
            visit_count=visit_count,
            course=course_name,
            booking_status=status,
        )

        messages.success(request, "予約を受け付けました。")
        return redirect("stores:customer_store_info", pk=store.id)

class customer_store_new_registerView(TemplateView):
    template_name = "stores/customer_store_new_register.html"


class customer_store_new_register_confirmView(TemplateView):
    template_name = "stores/customer_store_new_register_confirm.html"


# =========================
# company views
# =========================
class company_store_infoView(TemplateView):
    template_name = "stores/company_store_info.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["store"] = get_object_or_404(Store, pk=self.kwargs["pk"])
        return context


class company_store_managementView(TemplateView):
    template_name = "stores/company_store_management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query = self.request.GET.get("q", "").strip()
        if query:
            stores = Store.objects.filter(Q(store_name__icontains=query)).order_by("store_name")
        else:
            stores = Store.objects.all().order_by("store_name")

        context["stores"] = stores
        context["query"] = query
        return context


# =========================
# store views
# =========================
class store_basic_editView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    店舗基本情報 + 店舗画像(FormSet) + メニュー(FormSet)
    """
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

        # ★ prefix を固定（POST/FILES のキーと一致させる）
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

            # -----------------------
            # 店舗画像：保存（image_path 必須対策で "----" 補完）
            # -----------------------
            image_objs = image_formset.save(commit=False)
            for obj in image_objs:
                if not getattr(obj, "image_path", ""):
                    obj.image_path = "----"
                obj.store = store
                obj.save()

            # 削除（DB行）
            for obj in image_formset.deleted_objects:
                obj.delete()

            # -----------------------
            # メニュー：保存（image_path 必須対策で "----" 補完）
            # -----------------------
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

        # invalid：ここで理由が見えないと連打→messagesが溜まるので、
        # テンプレ側で formset errors を必ず表示してね（後述）
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

        today = timezone.localdate()

        # 今日のネット予約受付状況（日ごとの設定を優先）
        today_setting = StoreOnlineReservation.objects.filter(store=store, date=today).first()
        if today_setting is not None:
            context["is_online_open"] = bool(today_setting.booking_status)
            context["today_available_seats"] = int(today_setting.available_seats or 0)
        else:
            context["is_online_open"] = False
            context["today_available_seats"] = 0

        # 本日の予約一覧
        today_qs = (
            Reservation.objects
            .filter(store=store, visit_date=today)
            .select_related("booking_user")
            .order_by("start_time", "visit_time")
        )
        context["today_reservations"] = today_qs
        context["today_reservations_count"] = today_qs.count()

        # 月間予約数
        month_start = today.replace(day=1)
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1, day=1)

        context["month_reservations_count"] = (
            Reservation.objects.filter(store=store, visit_date__gte=month_start, visit_date__lt=next_month_start).count()
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
