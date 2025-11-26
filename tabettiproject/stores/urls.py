
from django.urls import path
from .views import *

app_name = "stores"

urlpatterns = [
    path("store_map/", store_mapView.as_view(), name="store_map"),
    path("store_menu_course/", store_menu_courseView.as_view(), name="store_menu_course"),
    path("store_basic_edit_custmer/", store_basic_edit_custmerView.as_view(), name="store_basic_edit_custmer"),
    path("store_basic_edit/", store_basic_editView.as_view(), name="store_basic_edit"),
    path("store_info_company/", store_info_companyView.as_view(), name="store_info_company"),
    path("store_info_customer/", store_info_customerView.as_view(), name="store_info_customer"),
    path("store_info_list/", store_info_listView.as_view(), name="store_info_list"),
    path("store_new_register/", store_new_registerView.as_view(), name="store_new_register"),
    path("store_new_register_confirm/", store_new_register_confirmView.as_view(), name="store_new_register_confirm"),
    path("store_top/", store_topView.as_view(), name="store_top"),  

]