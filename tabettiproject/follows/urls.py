from django.urls import path
from .views import *

app_name = "follows"
urlpatterns = [
    path("follow_list/", Customer_follow_listView.as_view(), name="customer_follow_list"),
    path("follower_list/", Customer_follower_listView.as_view(), name="customer_follower_list"),
]
