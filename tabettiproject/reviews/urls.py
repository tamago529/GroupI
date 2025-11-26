from django.urls import path
from .views import *

app_name = "reviews"

urlpatterns = [
    path("store_review_list/", review_list_customerView.as_view(), name="store_review_list"),
    path("reviewer_review_list/", review_list_reviewerView.as_view(), name="reviewer_review_list"),
    path("reviewer_detail/", reviewer_detailView.as_view(), name="reviewer_detail"),
    path("reviewer_search/", reviewer_searchView.as_view(), name="reviewer_search"),
    path("customer_review_report/", review_report_customerView.as_view(), name="customer_review_report"),
    path("store_review_report/", review_report_storeView.as_view(), name="store_review_report"),
    path("store_review_list_all/", review_list_storeView.as_view(), name="store_review_list_all"),
    path("company_review_list/", review_list_companyView.as_view(), name="company_review_list"),
    path("customer_report_input/", customer_report_input.as_view(), name="customer_report_input"),
    
]