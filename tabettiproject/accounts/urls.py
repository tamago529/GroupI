from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static

from . import views
app_name = "accounts"

urlpatterns = [

    path("", customer_loginView.as_view(), name="customer_login"),

    path("company_account_management/", company_account_managementView.as_view(), name="company_account_management"),
    path("company_login/", company_loginView.as_view(), name="company_login"),
    path("company/logout/", company_logout_view, name="company_logout"),
    path("company_store_review_detail/<int:request_id>/", company_store_review_detailView.as_view(), name="company_store_review_detail"),
    path("company_store_review/", company_store_reviewView.as_view(), name="company_store_review"),
    path("company_store_review/<int:request_id>/permit/",views.company_store_review_permitView.as_view(),name="company_store_review_permit",),
    path("company_store_review/<int:request_id>/reject/",views.company_store_review_rejectView.as_view(),name="company_store_review_reject",),
    path("store/password_reset/", views.storemail_sendView.as_view(), name="store_password_reset"),
    path("store/reset/<uidb64>/<token>/", views.store_password_reset_confirmView.as_view(), name="store_password_reset_confirm"),
    path("store/reset/done/", views.store_password_reset_completeView.as_view(), name="store_password_reset_complete"),
    path('account_delete_execute/<int:pk>/', views.account_delete_execute, name='account_delete_execute'),
    path("company_top/", company_topView.as_view(), name="company_top"),
    path("customer_login/", customer_loginView.as_view(), name="customer_login"),
    path("customer_logout/", customer_logout_view, name="customer_logout"),
    path("customer_register/", customer_registerView.as_view(), name="customer_register"),
    path("customer_settings/", customer_settingsView.as_view(), name="customer_settings"),
    path("customer_setting/", customer_settingsView.as_view(), name="customer_setting"), # エイリアス
    path("customer_mail_send/", customermail_sendView.as_view(), name="customer_mail_send"),
    path("customer_password_reset_complete/", customer_password_reset_completeView.as_view(), name="customer_password_reset_complete"),
    path("customer_password_reset_expire/", customer_password_reset_expireView.as_view(), name="customer_password_reset_expire"),
    path("customer_password_reset/", customer_password_resetView.as_view(), name="customer_password_reset"),
    path('password_reset/done/', views.customer_password_doneView.as_view(), name='customer_password_done'),
    path('reset/<uidb64>/<token>/', views.customer_password_resetView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.customer_password_reset_completeView.as_view(), name='customer_password_reset_complete'),
    path("store_account_edit/", store_account_editView.as_view(), name="store_account_edit"),
    path("store_login/", store_loginView.as_view(), name="store_login"),
    path("store_logout/", store_logout_view, name="store_logout"),
    path("store_register/", store_registerView.as_view(), name="store_register"),
    path("store_account_application_confirm/", store_account_application_confirmView.as_view(), name="store_account_application_confirm"),
    path("store_account_application_input/", store_account_application_inputView.as_view(), name="store_account_application_input"),
    path("store_account_application_message/", store_account_application_messageView.as_view(), name="store_account_application_message"),
    path("store_account_mail_sent/", store_account_mail_sentView.as_view(), name="store_account_mail_sent"),
    path("store_account_privacy/", store_account_privacyView.as_view(), name="store_account_privacy"),
    path("store-account/search/", views.store_account_searchView.as_view(), name="store_account_search"),
    path("store/reset/<uidb64>/<token>/", views.store_password_reset_confirmView.as_view(), name="store_password_reset_confirm"),
    path("store/mail-send/", views.storemail_sendView.as_view(), name="store_mail_send"),
    path("store/reset/complete/", views.store_password_reset_completeView.as_view(), name="store_password_reset_complete"),
    path("store-account/request/create/", views.store_account_request_createView.as_view(), name="store_account_request_create"),
    path("store_account_staff_confirm/" , store_account_staff_confirmView.as_view(),name="store_account_staff_confirm"),
    path("store_account_staff_input/",store_account_staff_inputView.as_view(),name="store_account_staff_input"),
    path("company_top/", company_topView.as_view(), name="company_top"),
    path("customer_top/", customer_topView.as_view(), name="customer_top"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
