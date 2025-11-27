from django.shortcuts import render

from django.views.generic.base import TemplateView

#共通機能の定義



class company_account_managementView(TemplateView):
    template_name = "company_account_management.html"

class company_loginView(TemplateView):
    template_name = "company_login.html"

class company_account_managementView(TemplateView):
    template_name = "company_account_management.html"

class company_loginView(TemplateView):
    template_name = "company_login.html"

class company_logoutView(TemplateView):
    template_name = "company_logout.html" 

class company_store_review_detailView(TemplateView):
    template_name = "company_store_review_detail.html"

class company_store_reviewView(TemplateView):
    template_name = "company_store_review.html"

class company_topView(TemplateView):
    template_name = "company_top.html"       

class customer_loginView(TemplateView):
    template_name = "customer_login.html"

class customer_logoutView(TemplateView):
    template_name = "customer_logout.html"

class customer_registerView(TemplateView):
    template_name = "customer_register.html"

class customer_settingsView(TemplateView):
    template_name = "customer_settings.html"

class customermail_sendView(TemplateView):
    template_name = "customer_mail_send.html"

class customer_password_reset_completeView(TemplateView):
    template_name = "customer_password_reset_complete.html"

class customer_password_reset_expireView(TemplateView):                    
    template_name = "customer_password_reset_expire.html"

class customer_password_resetView(TemplateView):
    template_name = "customer_password_reset.html"

class store_account_editView(TemplateView):
    template_name = "store_account_edit.html"

class store_loginView(TemplateView):
    template_name = "store_login.html"

class store_registerView(TemplateView):
    template_name = "store_register.html"

class store_account_application_confirmView(TemplateView):
    template_name = "store_account_application_confirm.html"

class store_account_application_inputView(TemplateView):
    template_name = "store_account_application_input.html"

class store_account_application_messageView(TemplateView):
    template_name = "store_account_application_message.html"

class store_account_mail_sentView(TemplateView):
    template_name = "store_account_mail_sent.html"

class store_account_privacyView(TemplateView):
    template_name = "store_account_privacy.html"

class store_account_searchView(TemplateView):
    template_name = "store_account_search.html"

class store_account_staff_confirmView(TemplateView):
    template_name = "tore_account_staff_confirm.html" 

class store_account_staff_inputView(TemplateView):
    template_name = "store_account_staff_input.html"

