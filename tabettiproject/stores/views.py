from __future__ import annotations

import calendar
import urllib.parse
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, UpdateView
from django.views.generic.base import TemplateView
from.form import CompanyStoreEditForm
from commons.models import (
    CustomerAccount,
    Reservation,
    Reservator,
    ReservationStatus,
    Store,
    StoreAccount,
    StoreImage,
    StoreMenu,
    StoreOnlineReservation,
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
# 予約：店舗トップ（顧客）
# -----------------------------
class customer_store_infoView(TemplateView):
    template_name = "stores/customer_store_info.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        store = get_object_or_404(Store, pk=self.kwargs["pk"])
        context["store"] = store

        # 店舗画像
        context["store_images"] = StoreImage.objects.filter(store=store).order_by("id")

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

        start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = date(year, month, last_day)

        # 受付中の日（過去日は除外）
        open_days = list(
            StoreOnlineReservation.objects.filter(
                store=store,
                date__range=(start, end),
                booking_status=True,
            ).values_list("date", flat=True)
        )
        open_days = [d for d in open_days if d >= today]
        context["open_days"] = [d.isoformat() for d in sorted(open_days)]

        # ログイン顧客（初期値用）
        context["login_customer"] = _get_customer_from_user(self.request.user)

        # JS側で使う
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

        # 過去月を丸める
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
        # 過去・現在時刻チェック
        # -------------------------
        today = timezone.localdate()
        now = timezone.localtime()

        if visit_date < today:
            messages.error(request, "過去の日付は予約できません。")
            return redirect("stores:customer_store_info", pk=store.id)

        if visit_date == today and visit_time < now.time():
            messages.error(request, "現在時刻より前の時刻は予約できません。")
            return redirect("stores:customer_store_info", pk=store.id)

        # -------------------------
        # 受付チェック
        # -------------------------
        setting = StoreOnlineReservation.objects.filter(store=store, date=visit_date).first()
        if not setting or not setting.booking_status:
            messages.error(request, "この日はネット予約を受け付けていません。")
            return redirect("stores:customer_store_info", pk=store.id)

        # -------------------------
        # 席数チェック（日単位合計）
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
        # コース名
        # -------------------------
        course_name = "1時間コース" if course_minutes == 60 else "2時間コース"

        start_dt = datetime.combine(visit_date, visit_time)
        end_dt = start_dt + timedelta(minutes=course_minutes)

        if end_dt.date() != visit_date:
            messages.error(request, "営業時間外の予約はできません（終了時刻が翌日になります）。")
            return redirect("stores:customer_store_info", pk=store.id)

        # -------------------------
        # 予約者（Reservator）を決める
        # -------------------------
        customer = _get_customer_from_user(request.user)
        reservator = None

        if customer:
            reservator = Reservator.objects.filter(customer_account=customer).first()

            if reservator is None:
                full_name = form.cleaned_data.get("full_name") or (customer.nickname or "")
                full_name_kana = form.cleaned_data.get("full_name_kana") or ""
                email = form.cleaned_data.get("email") or (customer.sub_email or customer.email or "")
                phone = form.cleaned_data.get("phone_number") or (customer.phone_number or "")

                # ログインでも補完できないなら入力必須
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
                # 空欄だけ補完
                changed = False
                if not reservator.full_name and form.cleaned_data.get("full_name"):
                    reservator.full_name = form.cleaned_data["full_name"]; changed = True
                if not reservator.full_name_kana and form.cleaned_data.get("full_name_kana"):
                    reservator.full_name_kana = form.cleaned_data["full_name_kana"]; changed = True
                if not reservator.email and form.cleaned_data.get("email"):
                    reservator.email = form.cleaned_data["email"]; changed = True
                if not reservator.phone_number and form.cleaned_data.get("phone_number"):
                    reservator.phone_number = form.cleaned_data["phone_number"]; changed = True
                if changed:
                    reservator.save()
        else:
            # 未ログイン → 全部必須
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
        # 予約ステータス
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
class company_store_infoView(UpdateView):
    model = Store
    form_class = CompanyStoreEditForm
    template_name = "stores/company_store_info.html"
    context_object_name = "store"

    def get_success_url(self):
        # 保存したら、また同じ画面（自分自身）を表示する
        messages.success(self.request, "店舗情報を更新しました。")
        return reverse('stores:company_store_info', kwargs={'pk': self.object.pk})


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

            # 店舗画像
            image_objs = image_formset.save(commit=False)
            for obj in image_objs:
                if not getattr(obj, "image_path", ""):
                    obj.image_path = "----"
                obj.store = store
                obj.save()
            for obj in image_formset.deleted_objects:
                obj.delete()

            # メニュー
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
