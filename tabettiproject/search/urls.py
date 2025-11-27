from django.urls import path
from .views import *

app_name = "search"

urlpatterns = [
  path("search/top/", customer_topView.as_view(), name="customer_top.html"),
  path("search/genre_list/", customer_genre_listView.as_view(), name="customer_genre_list.html"),
  path("search/search_list/", customer_search_listView.as_view(), name="customer_search_list.html")

]