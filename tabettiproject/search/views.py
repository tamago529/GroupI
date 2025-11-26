from django.shortcuts import render

from django.views.generic.base import TemplateView

class topView(TemplateView):
    template_name = "top.html"

class genre_listView(TemplateView):
    template_name =  "genre_list.html"

class search_listView(TemplateView):
    template_name = "search_list.html"       
