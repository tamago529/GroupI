from django.shortcuts import render

from django.views.generic.base import TemplateView

class 	reservation_calendarView(TemplateView):
    template_name = "reservation_calendar.html"

class 	reservation_ledgerView(TemplateView):
    template_name = "reservation_ledger.html"

class 	customer_ledgerView(TemplateView):
    template_name = "customer_ledger.html"

class 	reservation_settingsView(TemplateView):
    template_name = "reservation_settings.html"

class 	seat_settingsView(TemplateView):
    template_name = "seat_settings.html"