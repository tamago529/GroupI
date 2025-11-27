from django.shortcuts import render


from django.views.generic.base import TemplateView

class company_common_completeView(TemplateView):
    template_name = "company_common_complete.html"


class company_common_confirmView(TemplateView):
    template_name = "company_common_confirm.html"