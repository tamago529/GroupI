from django.urls import path
from . import views

app_name = "search"

urlpatterns = [
    # クラスベースビュー
    path(
        "customer_top/",
        views.customer_topView.as_view(),
        name="customer_top"
    ),
    path(
        "genre_list/",
        views.customer_genre_listView.as_view(),
        name="customer_genre_list"
    ),

]
