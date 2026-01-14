from django.shortcuts import render

from django.views.generic.base import TemplateView


class store_reservation_registerView(TemplateView):
    template_name = "reservations/store_reservation_register.html"


class store_reservation_confirmView(TemplateView):
    template_name = "reservations/store_reservation_confirm.html"


class store_reservation_editView(TemplateView):
    template_name = "reservations/store_reservation_edit.html"


class store_reservation_cancelView(TemplateView):
    template_name = "reservations/store_reservation_cancel.html"


class store_reservation_historyView(TemplateView):
    template_name = "reservations/store_reservation_history.html"

class store_topView(TemplateView):
    template_name = "reservations/store_top.html"    
