from django.shortcuts import render
from django.views.generic.base import TemplateView

class customer_mapView(TemplateView):
    template_name = "customer_map.html"
    
class customer_menu_courseView(TemplateView):
    template_name = "customer_menu_course.html"
    
class customer_store_basic_editView(TemplateView):
    template_name = "customer_store_basic_edit.html"

class store_basic_editView(TemplateView):
    template_name = "store_basic_edit.html"
    
class company_store_infoView(TemplateView):
    template_name = "company_store_info.html"
    
class customer_store_infoView(TemplateView):
    template_name = "customer_store_info.html"
    
class customer_store_new_registerView(TemplateView):
    template_name = "customer_store_new_register.html"
    
class customer_store_new_register_confirmView(TemplateView):
    template_name = "customer_store_new_register_confirm.html"
    
class store_topView(TemplateView):
    template_name = "store_top.html"

class company_store_managementView(TemplateView):
    template_name = "company_store_management.html"
