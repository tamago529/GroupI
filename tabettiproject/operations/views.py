from django.shortcuts import render


from django.views.generic.base import TemplateView


class operations_account_managementView(TemplateView):
    template_name = "operations_account_management.html"


class operations_common_complateView(TemplateView):
    template_name = "operations_common_complate.html"


class operations_common_confirmView(TemplateView):
    template_name = "common_confilm.html"


class operations_loginView(TemplateView):
    template_name = "operations_login.html"


class operations_store_managementView(TemplateView):
    template_name = "operations_store_management.html"


class operations_store_review_detailView(TemplateView):
    template_name = "operations_store_review_detail.html"


class operations_store_reviewView(TemplateView):
    template_name = "operations_store_review.html"


class operations_topView(TemplateView):
    template_name = "operations_top.html"


class reportView(TemplateView):
    template_name = "report.html"
