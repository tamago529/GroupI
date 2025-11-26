from django.urls import path
from .views import *

app_name = "reservations"

urlpatterns = [
    path("reservation_register/", reservation_registerView.as_view(), name="reservation_register"),
    path("reservation_confirm/", reservation_confirmView.as_view(), name="reservation_confirm"),
    path("reservation_edit/", reservation_editView.as_view(), name="reservation_edit"),
    path("reservation_cancel/", reservation_cancelView.as_view(), name="reservation_cancel"),
    path("reservation_history/", reservation_historyView.as_view(), name="reservation_history"),
]