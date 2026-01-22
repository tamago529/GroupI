from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.base import TemplateView
from commons.models import StoreAccount, Store, Reservation, StoreOnlineReservation
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone
from django.views.generic.edit import FormView
from .form import StoreBasicForm
from django.contrib import messages

import urllib.parse



class customer_mapView(TemplateView):
    template_name = "stores/customer_map.html"


class customer_menu_courseView(TemplateView):
    template_name = "stores/customer_menu_course.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 1. 店舗情報を取得
        store = get_object_or_404(Store, pk=self.kwargs['pk'])
        # 2. その店舗に紐づくメニューをすべて取得
        menu_items = StoreMenu.objects.filter(store=store)
        
        context['store'] = store
        context['menu_items'] = menu_items
        return context

class customer_store_basic_editView(TemplateView):
    template_name = "stores/customer_store_basic_edit.html"


def get_store_from_user(user) -> Store | None:
    if not user.is_authenticated:
        return None
    try:
        return user.storeaccount.store
    except Exception:
        return None


class store_basic_editView(LoginRequiredMixin, FormView):
    template_name = "stores/store_basic_edit.html"
    form_class = StoreBasicForm
    success_url = "/stores/store_basic_edit/"
    login_url = "accounts:store_login"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        store = get_store_from_user(self.request.user)
        kwargs["instance"] = store
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "店舗情報を保存しました。")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "入力内容にエラーがあります。")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["store"] = get_store_from_user(self.request.user)
        return context

class company_store_infoView(TemplateView):
    template_name = "stores/company_store_info.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["store"] = get_object_or_404(Store, pk=self.kwargs["pk"])
        return context


class customer_store_infoView(TemplateView):
    template_name = "stores/customer_store_info.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # URLの数字を使って店舗データを1件取得
        context['store'] = get_object_or_404(Store, pk=self.kwargs['pk'])
        return context

class customer_store_new_registerView(TemplateView):
    template_name = "stores/customer_store_new_register.html"


class customer_store_new_register_confirmView(TemplateView):
    template_name = "stores/customer_store_new_register_confirm.html"


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


class store_topView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "stores/store_top.html"
    login_url = 'accounts:store_login'

    def test_func(self):
        return is_store_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        store_account = self.request.user.storeaccount
        store = store_account.store
        context["store"] = store

        today = timezone.localdate()

        # -----------------------
        # 今日の「ネット予約受付中/停止中」
        # （日ごとの設定を優先）
        # -----------------------
        today_setting = StoreOnlineReservation.objects.filter(store=store, date=today).first()
        if today_setting is not None:
            context["is_online_open"] = bool(today_setting.booking_status)
            context["today_available_seats"] = int(today_setting.available_seats or 0)
        else:
            # 設定が無い日は「受付中」とする/停止とする…は運用次第。
            # いったん安全側で停止にしておくなら False に。
            context["is_online_open"] = False
            context["today_available_seats"] = 0

        # -----------------------
        # 本日の予約一覧（右カラム）
        # -----------------------
        today_qs = (
            Reservation.objects
            .filter(store=store, visit_date=today)
            .select_related("booking_user")
            .order_by("start_time", "visit_time")
        )
        context["today_reservations"] = today_qs

        # -----------------------
        # 集計（中央の来店情報など）
        # -----------------------
        context["today_reservations_count"] = today_qs.count()

        month_start = today.replace(day=1)
        # 月末算出（簡易）
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


class company_store_managementView(TemplateView):
    template_name = "stores/company_store_management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query = self.request.GET.get("q", "")

        if query:
            stores = Store.objects.filter(Q(store_name__icontains=query)).order_by("store_name")
        else:
            stores = Store.objects.all().order_by("store_name")

        context["stores"] = stores
        context["query"] = query
        return context


def store_delete_execute(request, pk):
    store = get_object_or_404(Store, pk=pk)
    name = store.store_name
    store.delete()

    msg = f"店舗「{name}」の削除"
    encoded_msg = urllib.parse.quote(msg)
    return redirect(reverse("commons:company_common_complete") + f"?message={encoded_msg}")

