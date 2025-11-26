from django.urls import path
from .views import *

app_name = "accounts"

urlpatterns = [
    path("admin_account_management/", admin_account_managementView.as_view(), name="admin_account_management)"),
    path("admin_login/", admin_loginView.as_view(), name="admin_login"),
    path("company_logout/", company_logoutView.as_view(), name="company_logout"),
    path("customer_login/", Customer_loginView.as_view(), name="customer_login"),
    path("customer_logout/", Customer_logoutView.as_view(), name="customer_logout"),
    path("customer_register/", customer_registerView.as_view(), name="customer_register"),
    path("customer_settings/", customer_settingsView.as_view(), name="customer_settings"),
    path("mail_send/", mail_sendView.as_view(), name="mail_send"),
    path("password_reset_complete/", password_reset_completeView.as_view(), name="password_reset_complete"),
    path("password_reset_expire/", password_reset_expireView.as_view(), name="password_reset_expire"),
    path("password_reset/", password_resetView.as_view(), name="password_reset"),
    path("store_account_edit/", store_account_editView.as_view(), name="store_account_edit"),
    path("store_login/", store_loginView.as_view(), name="store_login"),
    path("store_register/", store_registerView.as_view(), name="store_register"),
         
]