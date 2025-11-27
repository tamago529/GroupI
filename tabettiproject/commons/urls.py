from django.urls import path
from .views import *

app_name = "common"

urlpatterns = [
  path("commons/customer_common_complete/", customer_common_completeView.as_view(), name="customer_common_complete.html"),
  path("commons/customer_common_confirm/", customer_common_confirmView.as_view(), name="customer_common_confirm.html"),
  path("commons/error/", errorView.as_view(), name="error.html"),
  path("commons/store_common_complete/", store_common_completeView.as_view(), name='store_common_complete.html'),
  path("commons/store_common_confirm/", store_common_confirmView.as_view(), name='store_common_confirm.html')

]