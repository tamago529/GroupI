from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.base import TemplateView

from commons.models import Store, Area, Scene, CustomerAccount


def _get_customer_user(request: HttpRequest) -> CustomerAccount:
    """
    ログインユーザーが CustomerAccount であることを保証して返す
    （multi-table継承なので request.user が CustomerAccount になっている想定）
    """
    if not request.user.is_authenticated:
        raise Http404("ログインしてください。")

    # 念のため型チェック（CustomerAccountでなければ弾く）
    if not isinstance(request.user, CustomerAccount):
        raise Http404("顧客アカウントではありません。")

    return request.user


def _get_store_for_customer(customer: CustomerAccount, store_id: int) -> Store:
    """
    CustomerAccount(creator) が作成者の Store だけ取得できる
    """
    store = Store.objects.filter(pk=store_id, creator=customer).first()
    if not store:
        raise Http404("店舗が見つかりません（または権限がありません）。")
    return store


class store_restaurant_info_registerView(LoginRequiredMixin, TemplateView):
    """
    店舗情報 登録/編集（CustomerAccountが自分のstoreを編集する）
    URLに store_id が必要：
      /reservations/store_restaurant_info_register/3/
    """
    template_name = "reservations/store_restaurant_info_register.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = _get_customer_user(self.request)

        store_id = kwargs.get("store_id")
        store = _get_store_for_customer(customer, int(store_id))

        ctx.update(
            {
                "store": store,
                "areas": Area.objects.all().order_by("id"),
                "scenes": Scene.objects.all().order_by("id"),
            }
        )
        return ctx

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        customer = _get_customer_user(request)
        store_id = kwargs.get("store_id")
        store = _get_store_for_customer(customer, int(store_id))

        # --- フォーム値 ---
        store_name = (request.POST.get("store_name") or "").strip()
        branch_name = (request.POST.get("branch_name") or "").strip()

        email = (request.POST.get("email") or "").strip()
        phone_number = (request.POST.get("phone_number") or "").strip()
        address = (request.POST.get("address") or "").strip()

        map_location = (request.POST.get("map_location") or "").strip()

        area_id = (request.POST.get("area_id") or "").strip()
        scene_id = (request.POST.get("scene_id") or "").strip()

        business_hours = (request.POST.get("business_hours") or "").strip()

        seats_s = (request.POST.get("seats") or "").strip()
        budget_s = (request.POST.get("budget") or "").strip()

        reservable = (request.POST.get("reservable") == "1")
        editable = (request.POST.get("editable") == "1")

        # --- バリデーション（最低限） ---
        errors = []
        if not store_name:
            errors.append("店名は必須です。")
        if not phone_number:
            errors.append("電話番号は必須です。")
        if not address:
            errors.append("住所は必須です。")

        area = None
        if not area_id:
            errors.append("エリアは必須です。")
        else:
            area = Area.objects.filter(pk=area_id).first()
            if not area:
                errors.append("エリアが不正です。")

        scene = None
        if not scene_id:
            errors.append("利用シーンは必須です。")
        else:
            scene = Scene.objects.filter(pk=scene_id).first()
            if not scene:
                errors.append("利用シーンが不正です。")

        try:
            seats = int(seats_s) if seats_s != "" else 0
            if seats < 0:
                raise ValueError
        except ValueError:
            errors.append("席数は0以上の数字で入力してください。")
            seats = store.seats

        try:
            budget = int(budget_s) if budget_s != "" else 0
            if budget < 0:
                raise ValueError
        except ValueError:
            errors.append("予算は0以上の数字で入力してください。")
            budget = store.budget

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect("reservations:store_restaurant_info_register", store_id=store.id)

        # --- 保存 ---
        store.store_name = store_name
        store.branch_name = branch_name

        store.email = email
        store.phone_number = phone_number
        store.address = address

        store.map_location = map_location

        store.area = area  # type: ignore[assignment]
        store.scene = scene  # type: ignore[assignment]

        store.business_hours = business_hours
        store.seats = seats
        store.budget = budget

        store.reservable = reservable
        store.editable = editable

        store.save()
        messages.success(request, "店舗情報を保存しました。")
        return redirect("reservations:store_restaurant_info_register", store_id=store.id)
