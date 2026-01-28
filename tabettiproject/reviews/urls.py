from django.urls import path
from .views import *

app_name = "reviews"

urlpatterns = [
    path(
        "customer_review_list/",
        customer_review_listView.as_view(),
        name="customer_review_list",
    ),
    
    path("customer_store_preserve/", 
         customer_store_preserveView.as_view(), 
         name="customer_store_preserve"),

    path(
        "customer_reviewer_review_list/",
        customer_reviewer_review_listView.as_view(),
        name="customer_reviewer_review_list",
    ),
    path(
        "customer_reviewer_review_list/<int:customer_id>/",
        customer_reviewer_review_listView.as_view(),
        name="customer_reviewer_other_review_list",
    ),
    path(
    "customer_reviewer_detail/",
    customer_reviewer_detailView.as_view(),
    name="customer_reviewer_detail",
),

    path(
        "customer_reviewer_search/",
        customer_reviewer_searchView.as_view(),
        name="customer_reviewer_search",
    ),
    path(
        "customer_review_report/",
        customer_review_reportView.as_view(),
        name="customer_review_report",
    ),
    path(
        "customer_common_complete/",
        customer_common_completeView.as_view(),
        name="customer_common_complete",
    ),
    path(
        "store_review_report/<int:pk>/",
        store_review_reportView.as_view(),
        name="store_review_report",
    ),
    path(
        "store_review_list/<int:pk>/",
        store_review_listView.as_view(),
        name="store_review_list",
    ),
    path(
        "company_review_list/",
        company_review_listView.as_view(),
        name="company_review_list",
    ),
    path(
        "customer_report_input/",
        customer_report_input.as_view(),
        name="customer_report_input",
    ),

    path(
        "report/",
        reportView.as_view(),
        name="report"
    ),
      path('review_delete_execute/<int:pk>/', 
           review_delete_execute, 
           name='review_delete_execute'),
]
