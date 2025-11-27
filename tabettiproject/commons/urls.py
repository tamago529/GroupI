from django.urls import path
from .views import *

app_name = "common"

urlpatterns = [
  path("customer_common_complete/", customer_common_completeView.as_view(), name="customer_common_complete.html"),
  path("customer_common_confirm/", customer_common_confirmView.as_view(), name="customer_common_confirm.html"),
  path("error/", errorView.as_view(), name="error.html"),
  path("store_common_complete/", store_common_completeView.as_view(), name='store_common_complete.html'),
  path("store_common_confirm/", store_common_confirmView.as_view(), name='store_common_confirm.html')

]