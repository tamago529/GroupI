from django.shortcuts import render

from django.views.generic.base import TemplateView


class store_reservation_calendarView(TemplateView):
    template_name = "reservations_management/store_reservation_calendar.html"


class store_reservation_ledgerView(TemplateView):
    template_name = "reservations_management/store_reservation_ledger.html"


class store_customer_ledgerView(TemplateView):
    template_name = "reservations_management/store_customer_ledger.html"


class store_reservation_settingsView(TemplateView):
    template_name = "reservations_management/store_reservation_settings.html"


class store_seat_settingsView(TemplateView):
    template_name = "reservations_management/store_seat_settings.html"
