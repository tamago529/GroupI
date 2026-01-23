# stores/forms.py
from django import forms
from commons.models import Store, StoreImage, StoreMenu, StoreOnlineReservation
from django.forms import inlineformset_factory


class StoreBasicForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = [
            "store_name",
            "branch_name",
            "email",
            "phone_number",
            "address",
            "area",
            "business_hours",
            "open_time_1",
            "close_time_1",
            "open_time_2",
            "close_time_2",
            "seats",
            "budget",
            "scene",
            "reservable",
        ]

        widgets = {
            "business_hours": forms.TextInput(attrs={"placeholder": "例：月〜金 11:00-15:00"}),
            "open_time_1": forms.TimeInput(attrs={"type": "time"}),
            "close_time_1": forms.TimeInput(attrs={"type": "time"}),
            "open_time_2": forms.TimeInput(attrs={"type": "time"}),
            "close_time_2": forms.TimeInput(attrs={"type": "time"}),
        }

class StoreImageForm(forms.ModelForm):
    class Meta:
        model = StoreImage
        fields = ["image_file", "image_status"]


class StoreMenuForm(forms.ModelForm):
    class Meta:
        model = StoreMenu
        fields = ["menu_name", "price", "image_file"]


StoreImageFormSet = inlineformset_factory(
    Store,
    StoreImage,
    form=StoreImageForm,
    extra=3,
    can_delete=True,
)

StoreMenuFormSet = inlineformset_factory(
    Store,
    StoreMenu,
    form=StoreMenuForm,
    extra=5,
    can_delete=True,
)

COURSE_CHOICES = (
    ("60", "1時間コース"),
    ("120", "2時間コース"),
)

VISIT_COUNT_CHOICES = [(str(i), f"{i}名") for i in range(1, 11)]


class CustomerReserveForm(forms.Form):
    """
    顧客側 予約フォーム（customer_store_info.html のモーダル送信に対応）
    """
    visit_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date"})
    )
    visit_time = forms.TimeField(
        required=True,
        widget=forms.TimeInput(attrs={"type": "time"})
    )
    visit_count = forms.ChoiceField(
        required=True,
        choices=VISIT_COUNT_CHOICES
    )
    course_minutes = forms.ChoiceField(
        required=True,
        choices=COURSE_CHOICES
    )

    # 予約者情報（ログイン状況により必須化する）
    full_name = forms.CharField(required=False, max_length=100)
    full_name_kana = forms.CharField(required=False, max_length=100)
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(required=False, max_length=20)

    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3})
    )