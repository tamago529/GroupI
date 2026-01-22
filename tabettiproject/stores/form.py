# stores/forms.py
from django import forms
from commons.models import Store


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
