from django.urls import path
from .views import *

app_name = "follows"
urlpatterns = [
    path("follows/follow_list/", Customer_follow_listView.as_view(), name="customer_follow_list"),
    path("follows/follower_list/", Customer_follower_listView.as_view(), name="customer_follower_list"),
]
