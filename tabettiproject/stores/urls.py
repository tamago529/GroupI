from django.urls import path
from .views import (
    customer_mapView,
    customer_menu_courseView,
    customer_store_basic_editView,
    store_basic_editView,
    company_store_infoView,
    customer_store_infoView,
    customer_store_new_registerView,
    customer_store_new_register_confirmView,
    store_topView,
    company_store_managementView,
    store_info_listView,
    store_account_editView,
    store_logoutView,
    reservation_calendarView,
    reservation_ledgerView,
    store_review_listView,
)

app_name = "stores"

urlpatterns = [
    path("customer_map/", customer_mapView.as_view(), name="customer_map"),
    path("customer_menu_course/", customer_menu_courseView.as_view(), name="customer_menu_course"),
    path("customer_store_basic_edit/", customer_store_basic_editView.as_view(), name="customer_store_basic_edit"),
    path("store_basic_edit/", store_basic_editView.as_view(), name="store_basic_edit"),
    path("company_store_info/", company_store_infoView.as_view(), name="company_store_info"),
    path("customer_store_info/", customer_store_infoView.as_view(), name="customer_store_info"),
    path("customer_store_new_register/", customer_store_new_registerView.as_view(), name="customer_store_new_register"),
    path("customer_store_new_register_confirm/", customer_store_new_register_confirmView.as_view(), name="customer_store_new_register_confirm"),
    path("store_top/", store_topView.as_view(), name="store_top"),
    path("company_store_management/", company_store_managementView.as_view(), name="company_store_management"),
    path("store_info_list/", store_info_listView.as_view(), name="store_info_list"),
    path("store_account_edit/", store_account_editView.as_view(), name="store_account_edit"),
    path("store_logout/", store_logoutView.as_view(), name="store_logout"),
    path("reservation_calendar/", reservation_calendarView.as_view(), name="reservation_calendar"),
    path("reservation_ledger/", reservation_ledgerView.as_view(), name="reservation_ledger"),
    path("store_review_list/", store_review_listView.as_view(), name="store_review_list"),
]
