from django.shortcuts import render

from django.views.generic.base import TemplateView


class Customer_follow_listView(TemplateView):
    template_name = "follows/customer_follow_list.html"


class Customer_follower_listView(TemplateView):
    template_name = "follows/customer_follower_list.html"
