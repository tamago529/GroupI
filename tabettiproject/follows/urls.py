from django.urls import path
from .views import *

app_name = "follows"
urlpatterns = [
    path("follow_list/", Customer_follow_listView.as_view(), name="customer_follow_list"),
    path("follower_list/", Customer_follower_listView.as_view(), name="customer_follower_list"),

    # ✅ 追加：ユーザーのマイページ表示（customer_reviewer_detail.html を使う）
    path("user/<int:customer_id>/", Customer_user_pageView.as_view(), name="customer_user_page"),
]
