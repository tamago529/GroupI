from django.shortcuts import render

from django.views.generic.base import TemplateView

class customer_common_completeView(TemplateView):
    template_name = 'customer_commmon_complete.html'

class customer_common_confirmView(TemplateView):
    template_name = 'customer_commmon_confirm.html'

class errorView(TemplateView):
    template_name = 'error.html'

class store_common_completeView(TemplateView):
    template_name = 'store_common_complete.html'

class store_common_confirmView(TemplateView):
    template_name = 'store_common_confirm.html'            
