from django.urls import path
from .views import *

app_name = "stores"

urlpatterns = [
    # --- 顧客側 ---
    path("customer_map/", customer_mapView.as_view(), name="customer_map"),
    path("customer_menu_course/<int:pk>/", customer_menu_courseView.as_view(), name="customer_menu_course"),
    path("customer_store_info/<int:pk>/", customer_store_infoView.as_view(), name="customer_store_info"),
    path("customer_store_basic_edit/", customer_store_basic_editView.as_view(), name="customer_store_basic_edit"),
    path("customer_store_new_register/", customer_store_new_registerView.as_view(), name="customer_store_new_register"),
    path("customer_store_new_register_confirm/", customer_store_new_register_confirmView.as_view(), name="customer_store_new_register_confirm"),

    # --- 店舗側 ---
    path("store_basic_edit/", store_basic_editView.as_view(), name="store_basic_edit"),
    path("store_top/", store_topView.as_view(), name="store_top"),
    path("store_logout/", store_logoutView.as_view(), name="store_logout"),

    # --- 企業側 ---
    path("company_store_info/<int:pk>/", company_store_infoView.as_view(), name="company_store_info"),
    path("company_store_management/", company_store_managementView.as_view(), name="company_store_management"),
    path("company_store_delete_execute/<int:pk>/", store_delete_execute, name="store_delete_execute"),

    # =========================
    # 予約（追加）
    # =========================
    # カレンダー用：指定月の受付中日(JSON)
    path("availability/<int:store_id>/", StoreAvailabilityJsonView.as_view(), name="availability_json"),
    # 予約作成（POST）
    path("reserve/<int:store_id>/", CustomerReservationCreateView.as_view(), name="customer_reserve_create"),
]
