from django.urls import path
from .views import (
    store_reservation_historyView,
    store_reservation_confirmView,
    store_reservation_editView,
    store_reservation_cancelView,
)

app_name = "reservations"

urlpatterns = [
    # 予約一覧（履歴）
    path("store_reservation_history/", store_reservation_historyView.as_view(), name="store_reservation_history"),

    # 予約確認（詳細）
    path(
        "store_reservation_confirm/<int:reservation_id>/",
        store_reservation_confirmView.as_view(),
        name="store_reservation_confirm",
    ),

    # 予約変更
    path(
        "store_reservation_edit/<int:reservation_id>/",
        store_reservation_editView.as_view(),
        name="store_reservation_edit",
    ),

    # 予約キャンセル
    path(
        "store_reservation_cancel/<int:reservation_id>/",
        store_reservation_cancelView.as_view(),
        name="store_reservation_cancel",
    ),
]
