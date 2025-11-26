from django.shortcuts import render
from django.views import TemplateView

class review_list_customerView(TemplateView):
    template_name = "review_list_customer.html"

class review_list_reviewerView(TemplateView):
    template_name = "review_list_reviewer.html"

class reviewer_detailView(TemplateView):
    template_name = "reviewer_detail.html"

class reviewer_searchView(TemplateView):
    template_name = "reviewer_search.html"

class review_report_customerView(TemplateView):
    template_name = "review_report_customer.html"

class review_report_storeView(TemplateView):
    template_name = "review_report_store.html"

class review_list_storeView(TemplateView):
    template_name = "review_list_store.html"

class review_list_companyView(TemplateView):
    template_name = "review_list_company.html"

class customer_report_input(TemplateView):
    template_name = "customer_report_input.html"

