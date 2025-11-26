from django.urls import path
from .views import *

app_name = "operations"

urlpatterns = [
    path(
        "operations_account_management/",
        operations_account_managementView.as_view(),
        name="operations_account_management",
    ),
    path(
        "operations_common_complate/",
        operations_common_complateView.as_view(),
        name="operations_common_compalate",
    ),
    path(
        "operations_common_confirm/",
        operations_common_confirmView.as_view(),
        name="operations_common_confirm",
    ),
    path("operations_login/", operations_loginView.as_view(), name="operations_login"),
    path(
        "operations_store_management/",
        operations_store_managementView.as_view(),
        name="operations_store_management",
    ),
    path(
        "operations_store_review_detail/",
        operations_store_review_detailView.as_view(),
        name="operations_store_review_detail",
    ),
    path(
        "operations_store_review/",
        operations_store_reviewView.as_view(),
        name="operartions_store_review",
    ),
    path("operations_top/", operations_topView.as_view(), name="operations_top"),
    path("report/", reportView.as_view(), name="report"),
]
