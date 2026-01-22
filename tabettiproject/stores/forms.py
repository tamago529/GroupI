from django import forms
from commons.models import Store, Scene, Area


class StoreBasicForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = [
            "store_name",
            "branch_name",
            "email",
            "phone_number",
            "area",
            "address",
            "map_location",
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
            "open_time_1": forms.TimeInput(attrs={"type": "time"}),
            "close_time_1": forms.TimeInput(attrs={"type": "time"}),
            "open_time_2": forms.TimeInput(attrs={"type": "time"}),
            "close_time_2": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # マスタ選択をちゃんと「名前順」などにしたい場合
        self.fields["scene"].queryset = Scene.objects.all().order_by("scene_name")
        self.fields["area"].queryset = Area.objects.all().order_by("id")

        # 任意：ラベルを短く
        self.fields["map_location"].label = "地図URL/座標"
        self.fields["business_hours"].label = "営業時間(テキスト)"

        # 任意：placeholder
        self.fields["map_location"].widget.attrs.update({"placeholder": "例：GoogleMapのURL など"})
        self.fields["business_hours"].widget.attrs.update({"placeholder": "例：月〜金 10:00-18:00"})
