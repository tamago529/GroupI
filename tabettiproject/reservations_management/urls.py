from django.urls import path
from .views import (
    # カレンダー
    store_reservation_calendarView,

    # 台帳（トップ/日別/詳細/編集）
    store_reservation_ledgerView,

    store_reservation_ledger_dayView,

    store_reservation_detailView,

    # Phase3: 予約編集（GET/POST）
    store_reservation_editView,

    # Phase2: ステータス変更（POST）
    store_reservation_actionView,

    # その他
    store_customer_ledgerView,
    store_reservation_settingsView,
    store_seat_settingsView,
)

app_name = "reservations_management"

urlpatterns = [
    # ----------------------------
    # 予約カレンダー
    # ----------------------------
    path("reservation_calendar/", store_reservation_calendarView.as_view(), name="store_reservation_calendar"),


    # ----------------------------
    # 予約台帳
    # ----------------------------
    path("reservation_ledger/", store_reservation_ledgerView.as_view(), name="store_reservation_ledger"),

    # 日別
    path("reservation_ledger_day/", store_reservation_ledger_dayView.as_view(), name="store_reservation_ledger_day"),

    # 詳細
    path("reservation_detail/<int:pk>/", store_reservation_detailView.as_view(), name="store_reservation_detail"),

    # Phase3: 編集（GET/POST）
    path("reservation_edit/<int:pk>/", store_reservation_editView.as_view(), name="store_reservation_edit"),

    # Phase2: ステータス変更（POST）
    path("reservation_action/<int:pk>/", store_reservation_actionView.as_view(), name="store_reservation_action"),

    # ----------------------------
    # 顧客台帳
    # ----------------------------
    path("customer_ledger/", store_customer_ledgerView.as_view(), name="store_customer_ledger"),

    # ----------------------------
    # ネット予約受付設定
    # ----------------------------
    path("reservation_settings/", store_reservation_settingsView.as_view(), name="store_reservation_settings"),

    # ----------------------------
    # 席設定
    # ----------------------------
    path("seat_settings/", store_seat_settingsView.as_view(), name="store_seat_settings"),
]
