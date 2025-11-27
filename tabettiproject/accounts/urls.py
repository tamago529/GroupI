from django.urls import path
from .views import *

app_name = "accounts"

urlpatterns = [
    path("accounts/company_account_management/", company_account_managementView.as_view(), name="company_account_management)"),
    path("accounts/company_login/", company_loginView.as_view(), name="company_login"),
    path("accounts/company_logout/", company_logoutView.as_view(), name="company_logout"),
    path("accounts/customer_login/", customer_loginView.as_view(), name="customer_login"),
    path("accounts/customer_logout/", customer_logoutView.as_view(), name="customer_logout"),
    path("accounts/customer_register/", customer_registerView.as_view(), name="customer_register"),
    path("accounts/customer_settings/", customer_settingsView.as_view(), name="customer_settings"),
    path("accounts/customermail_send/", customermail_sendView.as_view(), name="customermail_send"),
    path("accounts/customer_password_reset_complete/", customer_password_reset_completeView.as_view(), name="customer_password_reset_complete"),
    path("accounts/customer_password_reset_expire/", customer_password_reset_expireView.as_view(), name="customer_password_reset_expire"),
    path("accounts/customer_password_reset/", customer_password_resetView.as_view(), name="customer_password_reset"),
    path("accounts/store_account_edit/", store_account_editView.as_view(), name="store_account_edit"),
    path("accounts/store_login/", store_loginView.as_view(), name="store_login"),
    path("accounts/store_register/", store_registerView.as_view(), name="store_register"),
    path("accounts/store_account_application_confirm/", store_account_application_confirmView.as_view(), name="store_account_application_confirm"),
    path("accounts/store_account_application_input/", store_account_application_inputView.as_view(), name="store_account_application_input"),
    path("accounts/store_account_application_message/", store_account_application_messageView.as_view(), name="store_account_application_message"),
    path("accounts/store_account_mail_sent/", store_account_mail_sentView.as_view(), name="tore_account_mail_sent"),
    path("accounts/store_account_privacy/", store_account_privacyView.as_view(), name="store_account_privacy"),
    path("accounts/store_account_search/", store_account_searchView.as_view(), name="store_account_search"),
    path("accounts/store_account_staff_confirm/" , store_account_staff_confirmView.as_view(),name="tore_account_staff_confirm"),
    path("accounts/store_account_staff_input/",store_account_staff_inputView.as_view(),name="store_account_staff_input")

]