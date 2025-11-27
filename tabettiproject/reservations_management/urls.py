from django.urls import path
from .views import *

app_name = "reservations_management"

urlpatterns = [
    path("reservations_management/reservation_calendar/", store_reservation_calendarView.as_view(), name="store_reservation_calendar"),
    path("reservations_management/reservation_ledger/", store_reservation_ledgerView.as_view(), name="store_reservation_ledger"),
    path("reservations_management/customer_ledger/", store_customer_ledgerView.as_view(), name="store_customer_ledger"),
    path("reservations_management/reservation_settings/", store_reservation_settingsView.as_view(), name="store_reservation_settings"),
    path("reservations_management/seat_settings/", store_seat_settingsView.as_view(), name="store_seat_settings"),
]