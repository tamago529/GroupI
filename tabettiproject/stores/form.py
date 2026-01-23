# stores/forms.py
from django import forms
from commons.models import Store, StoreImage, StoreMenu
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