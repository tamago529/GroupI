from django.urls import path
from .views import (
    # カレンダー
    store_reservation_calendarView,
    store_reservation_calendar_debugView,

    # 台帳（トップ/日別/詳細/編集）
    store_reservation_ledgerView,
    store_reservation_ledger_debugView,
    store_reservation_ledger_dayView,
    store_reservation_ledger_day_debugView,
    store_reservation_detailView,
    store_reservation_detail_debugView,

    # Phase3: 予約編集（GET/POST）
    store_reservation_editView,
    store_reservation_edit_debugView,

    # Phase2: ステータス変更（POST）
    store_reservation_actionView,
    store_reservation_action_debugView,

    # その他
    store_customer_ledgerView,
    store_reservation_settingsView,
    store_reservation_settings_debugView,
    store_seat_settingsView,
)

app_name = "reservations_management"

urlpatterns = [
    # ----------------------------
    # 予約カレンダー
    # ----------------------------
    path("reservation_calendar/", store_reservation_calendarView.as_view(), name="store_reservation_calendar"),
    path("reservation_calendar_debug/", store_reservation_calendar_debugView.as_view(), name="store_reservation_calendar_debug"),

    # ----------------------------
    # 予約台帳
    # ----------------------------
    path("reservation_ledger/", store_reservation_ledgerView.as_view(), name="store_reservation_ledger"),
    path("reservation_ledger_debug/", store_reservation_ledger_debugView.as_view(), name="store_reservation_ledger_debug"),

    # 日別
    path("reservation_ledger_day/", store_reservation_ledger_dayView.as_view(), name="store_reservation_ledger_day"),
    path("reservation_ledger_day_debug/", store_reservation_ledger_day_debugView.as_view(), name="store_reservation_ledger_day_debug"),

    # 詳細
    path("reservation_detail/<int:pk>/", store_reservation_detailView.as_view(), name="store_reservation_detail"),
    path("reservation_detail_debug/<int:pk>/", store_reservation_detail_debugView.as_view(), name="store_reservation_detail_debug"),

    # Phase3: 編集（GET/POST）
    path("reservation_edit/<int:pk>/", store_reservation_editView.as_view(), name="store_reservation_edit"),
    path("reservation_edit_debug/<int:pk>/", store_reservation_edit_debugView.as_view(), name="store_reservation_edit_debug"),

    # Phase2: ステータス変更（POST）
    path("reservation_action/<int:pk>/", store_reservation_actionView.as_view(), name="store_reservation_action"),
    path("reservation_action_debug/<int:pk>/", store_reservation_action_debugView.as_view(), name="store_reservation_action_debug"),

    # ----------------------------
    # 顧客台帳
    # ----------------------------
    path("customer_ledger/", store_customer_ledgerView.as_view(), name="store_customer_ledger"),

    # ----------------------------
    # ネット予約受付設定
    # ----------------------------
    path("reservation_settings/", store_reservation_settingsView.as_view(), name="store_reservation_settings"),
    path("reservation_settings_debug/", store_reservation_settings_debugView.as_view(), name="store_reservation_settings_debug"),

    # ----------------------------
    # 席設定
    # ----------------------------
    path("seat_settings/", store_seat_settingsView.as_view(), name="store_seat_settings"),
]
