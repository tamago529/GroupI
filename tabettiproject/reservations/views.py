from django.shortcuts import render

from django.views.generic.base import TemplateView

class 	reservation_registerView(TemplateView):
    template_name = "reservation_register.html"

class 	reservation_confirmView(TemplateView):
    template_name = "reservation_confirm.html"

class 	reservation_editView(TemplateView):
    template_name = "reservation_edit.html"

class 	reservation_cancelView(TemplateView):
    template_name = "reservation_cancel.html"

class 	reservation_historyView(TemplateView):
    template_name = "reservation_history.html"

