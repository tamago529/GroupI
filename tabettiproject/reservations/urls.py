from django.urls import path
from .views import *

app_name = "reservations"

urlpatterns = [
    path("store_reservation_register/", store_reservation_registerView.as_view(), name="store_reservation_register"),
    path("store_reservation_confirm/", store_reservation_confirmView.as_view(), name="store_reservation_confirm"),
    path("store_reservation_edit/", store_reservation_editView.as_view(), name="store_reservation_edit"),
    path("store_reservation_cancel/", store_reservation_cancelView.as_view(), name="store_reservation_cancel"),
    path("store_reservation_history/", store_reservation_historyView.as_view(), name="store_reservation_history"),
    path("store_top/", store_topView.as_view(), name="store_top"),
]