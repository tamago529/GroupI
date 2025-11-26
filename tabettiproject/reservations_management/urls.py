from django.urls import path
from .views import *

app_name = "reservations_management"

urlpatterns = [
    path("reservation_calendar/", reservation_calendarView.as_view(), name="reservation_calendar"),
    path("reservation_ledger/", reservation_ledgerView.as_view(), name="reservation_ledger"),
    path("customer_ledger/", customer_ledgerView.as_view(), name="customer_ledger"),
    path("reservation_settings/", reservation_settingsView.as_view(), name="reservation_settings"),
    path("seat_settings/", seat_settingsView.as_view(), name="seat_settings"),
]