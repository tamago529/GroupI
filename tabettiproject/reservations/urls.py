from django.urls import path
from .views import (
    store_restaurant_info_registerView,
)

app_name = "reservations"

urlpatterns = [
    # 店舗情報登録（customerが自分のstoreを編集）
    path(
        "store_restaurant_info_register/<int:store_id>/",
        store_restaurant_info_registerView.as_view(),
        name="store_restaurant_info_register",
    ),
]

