from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse

from .models import (
    Account,
    CustomerAccount,
    StoreAccount,
    CompanyAccount,
    Store,
    Review,
    ReviewPhoto,
    ReviewReport,
    Follow,
    Reservator,
    Reservation,
    StoreOnlineReservation,
    StoreImage,
    StoreMenu,
    StoreAccountRequest,
    StoreAccountRequestLog,
    PasswordResetLog,
    TempRequestMailLog,
    AgeGroup,
    Gender,
    AccountType,
    Scene,
    Area,
    ReservationStatus,
    ImageStatus,
    ApplicationStatus,
)

# ==========================================================
# Account 追加用フォーム（ここが今回の本丸）
# account_type を必須化して保存前に止める
# ==========================================================
from django import forms
from django.contrib.auth.password_validation import validate_password

from django import forms
from django.contrib.auth.password_validation import validate_password

# admin.py の先頭付近（StoreAccountInlineFormSet より上！）
from .models import AccountType

def get_store_type():
    # DB作り直し直後でも落ちないようにする
    return AccountType.objects.get_or_create(account_type="店舗")[0]



class AccountCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = Account
        fields = ("username", "email", "account_type")

    def clean_account_type(self):
        v = self.cleaned_data.get("account_type")
        if v is None:
            raise forms.ValidationError("アカウント種別（account_type）は必須です。")
        return v

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")

        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords don't match")

        if p1:
            validate_password(p1)

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)

        # ★本丸：UserAdminの追加フローで落ちるのを防ぐ（必ず反映）
        user.account_type = self.cleaned_data.get("account_type")

        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["account_type"].required = True

# ==========================================================
# StoreAccount Inline（Account 追加/編集画面に表示）
# ==========================================================
class StoreAccountInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        try:
            store_type = get_store_type()
        except AccountType.DoesNotExist:
            return

        if getattr(self.instance, "account_type_id", None) != store_type.id:
            return

        has_valid = False
        for f in self.forms:
            if not hasattr(f, "cleaned_data"):
                continue
            if f.cleaned_data.get("DELETE"):
                continue
            if f.cleaned_data.get("store"):
                has_valid = True
                break

        if not has_valid:
            raise ValidationError("アカウント種別が「店舗」の場合、店舗情報（StoreAccount）を入力してください。")


class StoreAccountInline(admin.StackedInline):
    model = StoreAccount
    fk_name = "account_ptr"  # 多テーブル継承の親リンク（通常これ）
    formset = StoreAccountInlineFormSet

    extra = 0
    max_num = 1
    can_delete = True

    fields = ("store", "admin_email", "permission_flag")
    autocomplete_fields = ("store",)


# ==========================================================
# AccountAdmin（親）
# 重要：add_form を自作フォームに差し替える
# ==========================================================
@admin.register(Account)
class AccountAdmin(UserAdmin):
    model = Account
    inlines = [StoreAccountInline]

    # ★ここが重要：追加フォームを差し替え
    add_form = AccountCreationForm

    list_display = ("id", "username", "email", "account_type", "is_staff", "is_active")
    search_fields = ("username", "email")
    ordering = ("id",)

    # 追加（作成）画面：Account のフィールドだけ
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "account_type", "password1", "password2", "is_staff", "is_active"),
        }),
    )

    # 変更（編集）画面
    fieldsets = UserAdmin.fieldsets + (
        (_("追加情報"), {"fields": ("account_type",)}),
    )

    def add_view(self, request, form_url="", extra_context=None):
        if request.method != "POST":
            return super().add_view(request, form_url, extra_context)

        FormClass = self.get_form(request, obj=None, change=False)
        form = FormClass(request.POST, request.FILES)

        # Inline 側のバリデーションが必要ならここで formsets を作る（今回はまず account_type を直すのが目的）
        if not form.is_valid():
            # ふつうにエラー表示させる
            return super().add_view(request, form_url, extra_context)

        # ★必ずフォームの save を通す（account_type を確実にセット）
        obj = form.save(commit=False)

        # ここでも保険（万一フォームが壊れてても DB へ行かせない）
        if obj.account_type_id is None:
            form.add_error("account_type", "アカウント種別（account_type）は必須です。")
            return super().add_view(request, form_url, extra_context)

        # UserAdmin で必要な属性処理を反映
        self.save_model(request, obj, form, change=False)

        messages.success(request, "アカウントを作成しました。")
        # 追加後は変更画面に飛ばす（好みで一覧でもOK）
        return redirect(reverse("admin:commons_account_change", args=[obj.pk]))

    

# ==========================================================
# 子モデルは単独追加禁止（誤作成防止）
# ==========================================================
class MultiTableChildNoAddMixin:
    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        if not change:
            raise ValidationError("このモデルは管理画面から直接追加できません。Account から作成してください。")
        super().save_model(request, obj, form, change)


@admin.register(CustomerAccount)
class CustomerAccountAdmin(MultiTableChildNoAddMixin, admin.ModelAdmin):
    list_display = ("id", "nickname", "username", "email", "phone_number", "age_group")
    search_fields = ("nickname", "username", "email")
    readonly_fields = ("username",)


@admin.register(StoreAccount)
class StoreAccountAdmin(MultiTableChildNoAddMixin, admin.ModelAdmin):
    list_display = ("id", "username", "store", "admin_email", "permission_flag")
    search_fields = ("username", "admin_email")
    readonly_fields = ("username",)


@admin.register(CompanyAccount)
class CompanyAccountAdmin(MultiTableChildNoAddMixin, admin.ModelAdmin):
    list_display = ("id", "company_name", "username", "email")
    search_fields = ("company_name", "username", "email")
    readonly_fields = ("username",)


# ==========================================================
# 以降：通常モデル（あなたのままでOK）
# ==========================================================
@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("id", "store_name", "branch_name", "area", "creator")
    search_fields = ("store_name", "branch_name", "email")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "reviewer", "store", "score", "posted_at")
    search_fields = ("reviewer__nickname", "store__store_name")


@admin.register(ReviewPhoto)
class ReviewPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "review", "image_path")


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ("id", "review", "reporter", "report_status", "reported_at")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("id", "follower", "followee", "is_blocked", "is_muted", "followed_at")


@admin.register(Reservator)
class ReservatorAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "email", "phone_number")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "booking_user", "store", "visit_date", "visit_time", "visit_count", "booking_status")


@admin.register(StoreOnlineReservation)
class StoreOnlineReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "booking_status", "available_seats", "date")


@admin.register(StoreImage)
class StoreImageAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "image_path", "image_status")


@admin.register(StoreMenu)
class StoreMenuAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "menu_name", "price")


@admin.register(StoreAccountRequest)
class StoreAccountRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "requester", "store_name", "phone_number", "requested_at")


@admin.register(StoreAccountRequestLog)
class StoreAccountRequestLogAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "request_status", "updated_at")


@admin.register(PasswordResetLog)
class PasswordResetLogAdmin(admin.ModelAdmin):
    list_display = ("reset_token", "account", "expires_at", "used_flag")


@admin.register(TempRequestMailLog)
class TempRequestMailLogAdmin(admin.ModelAdmin):
    list_display = ("temp_request_token", "requester", "expires_at", "used_flag")


# マスタ系
admin.site.register(AgeGroup)
admin.site.register(Gender)
admin.site.register(AccountType)
admin.site.register(Scene)
admin.site.register(Area)
admin.site.register(ReservationStatus)
admin.site.register(ImageStatus)
admin.site.register(ApplicationStatus)
