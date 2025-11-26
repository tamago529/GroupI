from django.urls import path
from .views import *

app_name = "follows"
urlpatterns = [
    path("follow_list/", follow_listView.as_view(), name="follow_list"),
    path("follower_list/", follower_listView.as_view(), name="follower_list"),
]
