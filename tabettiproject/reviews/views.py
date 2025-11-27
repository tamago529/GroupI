from django.shortcuts import render
from django.views.generic.base import TemplateView


class customer_review_listView(TemplateView):
    template_name = "reviews/customer_review_list.html"


class customer_reviewer_review_listView(TemplateView):
    template_name = "reviews/customer_reviewer_review_list.html"


class customer_reviewer_detailView(TemplateView):
    template_name = "reviews/customer_reviewer_detail.html"


class customer_reviewer_searchView(TemplateView):
    template_name = "reviews/customer_reviewer_search.html"


class customer_review_reportView(TemplateView):
    template_name = "reviews/customer_review_report.html"


class store_review_reportView(TemplateView):
    template_name = "reviews/store_review_report.html"


class store_review_listView(TemplateView):
    template_name = "reviews/store_review_list.html"


class company_review_listView(TemplateView):
    template_name = "reviews/company_review_list.html"


class customer_report_input(TemplateView):
    template_name = "reviews/customer_report_input.html"
