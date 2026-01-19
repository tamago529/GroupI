from django.urls import path
from .views import (
    store_topView,
    store_reservation_registerView,
    store_reservation_confirmView,
    store_reservation_editView,
    store_reservation_cancelView,
    store_reservation_historyView,
    store_pageView,
    store_restaurant_info_registerView,
)

app_name = "reservations"

urlpatterns = [
    path("store_top/", store_topView.as_view(), name="store_top"),

    # 店舗ページ（リンク用：最低限）
    path("store/<int:store_id>/", store_pageView.as_view(), name="store_page"),

    # 予約フロー
    path("store_reservation_register/", store_reservation_registerView.as_view(), name="store_reservation_register"),
    path("store_reservation_confirm/<int:pk>/", store_reservation_confirmView.as_view(), name="store_reservation_confirm"),
    path("store_reservation_edit/<int:pk>/", store_reservation_editView.as_view(), name="store_reservation_edit"),
    path("store_reservation_cancel/<int:pk>/", store_reservation_cancelView.as_view(), name="store_reservation_cancel"),
    path("store_reservation_history/", store_reservation_historyView.as_view(), name="store_reservation_history"),

    # ✅ 店舗情報（CustomerAccountが自分の作成店舗を編集）
    path(
        "store_restaurant_info_register/<int:store_id>/",
        store_restaurant_info_registerView.as_view(),
        name="store_restaurant_info_register",
    ),
]
