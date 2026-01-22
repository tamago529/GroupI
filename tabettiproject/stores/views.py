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

from commons.models import (
    Reservation,
    Store,
    StoreAccount,
    StoreImage,
    StoreMenu,
    StoreOnlineReservation,
)

from .form import StoreBasicForm, StoreImageFormSet, StoreMenuFormSet


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


class customer_store_infoView(TemplateView):
    template_name = "stores/customer_store_info.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        store = get_object_or_404(Store, pk=self.kwargs["pk"])
        context["store"] = store

        # ★ 追加：この店舗に紐づく画像一覧
        context["store_images"] = (
            StoreImage.objects
            .filter(store=store)
            .order_by("id")
        )

        return context

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
