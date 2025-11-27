from django.urls import path
from .views import *

app_name = "operations"

urlpatterns = [
    path(
        "company_common_complete/",
        company_common_completeView.as_view(),
        name="operations_common_compalete",
    ),
    path(
        "company_common_confirm/",
        company_common_confirmView.as_view(),
        name="operations_common_confirm",
    ),
]
