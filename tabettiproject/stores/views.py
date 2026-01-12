from django.shortcuts import render
from django.views.generic.base import TemplateView


class customer_mapView(TemplateView):
    template_name = "stores/customer_map.html"


class customer_menu_courseView(TemplateView):
    template_name = "stores/customer_menu_course.html"


class customer_store_basic_editView(TemplateView):
    template_name = "stores/customer_store_basic_edit.html"


class store_basic_editView(TemplateView):
    template_name = "stores/store_basic_edit.html"


class company_store_infoView(TemplateView):
    template_name = "stores/company_store_info.html"


class customer_store_infoView(TemplateView):
    template_name = "stores/customer_store_info.html"


class customer_store_new_registerView(TemplateView):
    template_name = "stores/customer_store_new_register.html"


class customer_store_new_register_confirmView(TemplateView):
    template_name = "stores/customer_store_new_register_confirm.html"


class store_topView(TemplateView):
    template_name = "stores/store_top.html"


class company_store_managementView(TemplateView):
    template_name = "stores/company_store_management.html"

class store_info_listView(TemplateView):
    template_name = "stores/store_info_list.html"

class store_account_editView(TemplateView):
    template_name = "stores/store_account_edit.html"

class store_logoutView(TemplateView):
    template_name = "stores/store_logout.html"    

class reservation_calendarView(TemplateView):
    template_name = "stores/reservation_calendar.html"

class reservation_ledgerView(TemplateView):
    template_name = "stores/reservation_ledger.html"

class store_review_listView(TemplateView):
    template_name = "stores/store_review_list.html"