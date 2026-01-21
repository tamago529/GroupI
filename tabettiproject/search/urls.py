from django.urls import path
from . import views
from .views import customer_search_listView

app_name = "search"

urlpatterns = [
    path("genre/", views.genre_list, name="customer_genre_list"),

    path("search_list/", customer_search_listView, name="customer_search_list"),

]
