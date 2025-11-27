from django.shortcuts import render

from django.views.generic.base import TemplateView


class customer_topView(TemplateView):
    template_name = "search/customer_top.html"


class customer_genre_listView(TemplateView):
    template_name = "search/customer_genre_list.html"


class customer_search_listView(TemplateView):
    template_name = "search/customer_search_list.html"
