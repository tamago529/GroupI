from django.urls import path
from .views import *

app_name = "search"

urlpatterns = [
  path("top/", topView.as_view(), name="top.html"),
  path("genre_list/", genre_listView.as_view(), name="genre_list.html"),
  path("search_list/", search_listView.as_view(), name="search_list.html")

]