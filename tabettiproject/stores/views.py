from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin , UserPassesTestMixin
from django.views.generic.base import TemplateView
from commons.models import StoreAccount

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

def is_store_user(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    try:
        _ = user.storeaccount
        return True
    except StoreAccount.DoesNotExist:
        return False
    except Exception:
        return False

class store_topView(LoginRequiredMixin,UserPassesTestMixin,TemplateView):
    template_name = "stores/store_top.html"
    login_url = 'accounts:store_login'

    def test_func(self):
        return is_store_user(self.request.user)

class store_logoutView(TemplateView):
    template_name = "accounts/store_logout.html"    

class company_store_managementView(TemplateView):
    template_name = "stores/company_store_management.html"
