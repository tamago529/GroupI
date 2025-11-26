from django.shortcuts import render
from django.views.generic.base import TemplateView

class store_mapView(TemplateView):
    template_name = "store_map.html"
    
class store_menu_courseView(TemplateView):
    template_name = "store_menu_course.html"
    
class store_basic_edit_custmerView(TemplateView):
    template_name = "store_basic_edit_custmer.html"

class store_basic_editView(TemplateView):
    template_name = "store_basic_edit.html"
    
class store_info_companyView(TemplateView):
    template_name = "store_info_company.html"
    
class store_info_customerView(TemplateView):
    template_name = "store_info_customer.html"
    
class store_info_listView(TemplateView):
    template_name = "store_info_list.html"
    
class store_new_registerView(TemplateView):
    template_name = "store_new_register.html"
    
class store_new_register_confirmView(TemplateView):
    template_name = "store_new_register_confirm.html"
    
class store_topView(TemplateView):
    template_name = "store_top.html"