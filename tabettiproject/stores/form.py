from django import forms
from django.forms import inlineformset_factory

from commons.models import Store, StoreImage, StoreMenu


# ============================================================
# 運用管理（Company）側：店舗編集フォーム
#  - Store のフィールドに完全一致（genre / open_time_2 / close_time_2 も含む）
# ============================================================
class CompanyStoreEditForm(forms.ModelForm):
    """
    運用管理側が店舗情報を編集するためのフォーム
    """
    class Meta:
        model = Store
        fields = [
            "store_name",
            "branch_name",
            "area",
            "genre",
            "address",
            "phone_number",
            "email",
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
            "store_name": forms.TextInput(attrs={"placeholder": "店舗名を入力"}),
            "branch_name": forms.TextInput(attrs={"placeholder": "支店名を入力"}),
            "address": forms.TextInput(attrs={"placeholder": "住所を入力"}),
            "phone_number": forms.TextInput(attrs={"placeholder": "電話番号を入力"}),
            "email": forms.EmailInput(attrs={"placeholder": "メールアドレスを入力"}),

            "business_hours": forms.Textarea(
                attrs={"rows": 2, "placeholder": "営業時間（自由記述）例）11:00-15:00 / 17:00-22:00"}
            ),

            "open_time_1": forms.TimeInput(attrs={"type": "time"}),
            "close_time_1": forms.TimeInput(attrs={"type": "time"}),
            "open_time_2": forms.TimeInput(attrs={"type": "time"}),
            "close_time_2": forms.TimeInput(attrs={"type": "time"}),

            "seats": forms.NumberInput(attrs={"min": 0}),
            "budget": forms.NumberInput(attrs={"min": 0, "placeholder": "￥"}),

            "genre": forms.TextInput(attrs={"placeholder": "カフェ、焼肉など"}),
            "reservable": forms.CheckboxInput(attrs={"style": "width: auto;"}),
        }


# ============================================================
# 店舗（Store）側：基本情報フォーム
#  - CompanyStoreEditForm と同じ fields に統一
# ============================================================
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
            "genre",
            "scene",
            "reservable",
        ]
        widgets = {
            "business_hours": forms.TextInput(
                attrs={"placeholder": "例：月〜金 11:00-15:00 / 17:00-22:00"}
            ),
            "open_time_1": forms.TimeInput(attrs={"type": "time"}),
            "close_time_1": forms.TimeInput(attrs={"type": "time"}),
            "open_time_2": forms.TimeInput(attrs={"type": "time"}),
            "close_time_2": forms.TimeInput(attrs={"type": "time"}),

            "genre": forms.TextInput(attrs={"placeholder": "カフェ、焼肉など"}),
        }


# ============================================================
# 店舗画像 / メニュー Form
# ============================================================
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


# ============================================================
# 顧客予約フォーム：コース 30/60/90/120/150
# ============================================================
COURSE_CHOICES = (
    ("30", "30分コース"),
    ("60", "1時間コース"),
    ("90", "1時間30分コース"),
    ("120", "2時間コース"),
    ("150", "2時間30分コース"),
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
