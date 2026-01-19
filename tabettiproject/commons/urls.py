from django.urls import path
from .views import *

app_name = "commons"

urlpatterns = [
    path("customer_common_complete/", customer_common_completeView.as_view(), name="customer_common_complete"),
    path("customer_common_confirm/", customer_common_confirmView.as_view(), name="customer_common_confirm"),
    path("error/", errorView.as_view(), name="error"),
    path("store_common_complete/", store_common_completeView.as_view(), name="store_common_complete"),
    path("store_common_confirm/", store_common_confirmView.as_view(), name="store_common_confirm"),

    path("company_common_complete/", company_common_completeView.as_view(), name="company_common_complete"),
    path("company_common_confirm/", company_common_confirmView.as_view(), name="company_common_confirm"),

    # ✅ 口コミ削除
    path("review_delete_confirm/<int:review_id>/", ReviewDeleteConfirmView.as_view(), name="review_delete_confirm"),
    path("review_delete_execute/<int:review_id>/", ReviewDeleteExecuteView.as_view(), name="review_delete_execute"),
    path("review_delete_complete/", ReviewDeleteCompleteView.as_view(), name="review_delete_complete"),
]
