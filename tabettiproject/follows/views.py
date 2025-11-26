from django.shortcuts import render

from django.views.generic.base import TemplateView

class 	follow_listView(TemplateView):
    template_name = "follow_list.html"

class 	follower_listView(TemplateView):
    template_name = "follower_list.html"