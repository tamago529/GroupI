from django.shortcuts import render

from django.views.generic.base import TemplateView

class customer_common_completeView(TemplateView):
    template_name = 'commons/customer_common_complete.html'

class customer_common_confirmView(TemplateView):
    template_name = 'commons/customer_common_confirm.html'

class errorView(TemplateView):
    template_name = 'commons/error.html'

class store_common_confirmView(TemplateView):
    template_name = 'commons/store_common_confirm.html'

class store_common_completeView(TemplateView):
    template_name = 'commons/store_common_complete.html'

class company_common_confirmView(TemplateView):
    template_name = 'commons/company_common_confirm.html' 

class company_common_completeView(TemplateView):
    template_name = 'commons/company_common_complete.html'
