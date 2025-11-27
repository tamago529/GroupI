
from django.urls import path
from .views import *

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
    path("company_store_management/", company_store_managementView.as_view(), name="company_store_management",
    ),

]