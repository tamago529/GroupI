from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _

from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

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
    return AccountType.objects.get(account_type="店舗")

STORE_TYPE_NAME = "店舗"

def is_store_type(account) -> bool:
    return bool(
        getattr(account, "account_type", None)
        and account.account_type.account_type == STORE_TYPE_NAME
    )




class AccountCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    # ★追加：店舗用入力欄
    store = forms.ModelChoiceField(queryset=Store.objects.all(), required=False, label="店舗（店舗アカウント用）")
    admin_email = forms.EmailField(required=False, label="管理者メール（店舗アカウント用）")
    permission_flag = forms.BooleanField(required=False, label="権限フラグ（店舗アカウント用）")

    class Meta:
        model = Account
        fields = ("username", "email", "account_type")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["account_type"].required = True

    def clean_account_type(self):
        v = self.cleaned_data.get("account_type")
        if v is None:
            raise forms.ValidationError("アカウント種別（account_type）は必須です。")
        return v

    def clean(self):
        cleaned = super().clean()

        # パスワードチェック
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")

        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords don't match")

        if p1:
            validate_password(p1)

        # ★店舗なら store 必須
        account_type = cleaned.get("account_type")
        store = cleaned.get("store")

        if account_type and account_type.account_type == "店舗":
         if store is None:
            self.add_error("store", "店舗アカウントの場合、店舗（store）は必須です。")

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)

        # ★本丸：UserAdmin追加フローで落ちるのを防ぐ（必ず反映）
        user.account_type = self.cleaned_data.get("account_type")

        # パスワード保存
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

            # ★店舗なら StoreAccount を自動作成
            store_type = AccountType.objects.filter(account_type="店舗").first()
            if store_type and user.account_type_id == store_type.id:
                store = self.cleaned_data.get("store")
                admin_email = self.cleaned_data.get("admin_email") or user.email
                permission_flag = bool(self.cleaned_data.get("permission_flag"))

                # store は clean() で必須にしてるが保険
                if store is None:
                    raise ValidationError("店舗アカウントの場合、店舗（store）は必須です。")

                StoreAccount.objects.update_or_create(
                    account_ptr=user,
                    defaults={
                        "store": store,
                        "admin_email": admin_email,
                        "permission_flag": permission_flag,
                    }
                )

        return user
    

class AccountChangeForm(UserChangeForm):
    # ★編集画面でも店舗情報を入力できるようにする
    store = forms.ModelChoiceField(queryset=Store.objects.all(), required=False, label="店舗（店舗アカウント用）")
    admin_email = forms.EmailField(required=False, label="管理者メール（店舗アカウント用）")
    permission_flag = forms.BooleanField(required=False, label="権限フラグ（店舗アカウント用）")

    class Meta:
        model = Account
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 既に StoreAccount があるなら初期値を入れる
        obj = self.instance
        if obj and obj.pk and hasattr(obj, "storeaccount"):
            sa = obj.storeaccount
            self.fields["store"].initial = sa.store_id
            self.fields["admin_email"].initial = sa.admin_email
            self.fields["permission_flag"].initial = sa.permission_flag

    def clean(self):
        cleaned = super().clean()

        # ★店舗なら store 必須（編集でも強制）
        account_type = cleaned.get("account_type")
        store = cleaned.get("store")

        store_type = AccountType.objects.filter(account_type="店舗").first()
        if store_type and account_type and account_type.id == store_type.id:
            if store is None:
                self.add_error("store", "店舗アカウントの場合、店舗（store）は必須です。")

        return cleaned


# ==========================================================
# StoreAccount Inline（Account 追加/編集画面に表示）
# ==========================================================
class StoreAccountInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        return


class StoreAccountInline(admin.StackedInline):
    model = StoreAccount
    fk_name = "account_ptr"  # 多テーブル継承の親リンク（通常これ）
    #formset = StoreAccountInlineFormSet

    extra = 1
    max_num = 1
    can_delete = True

    fields = ("store", "admin_email", "permission_flag")
    readonly_fields = ("store", "admin_email", "permission_flag")

    def has_add_permission(self, request, obj=None):
        return False

    # ★Inlineで編集させない（念のため）
    def has_change_permission(self, request, obj=None):
        return True  # 表示自体は許可（これをFalseにするとinlineごと消えることがある）

# ==========================================================
# AccountAdmin（親）
# 重要：add_form を自作フォームに差し替える
# ==========================================================
@admin.register(Account)
class AccountAdmin(UserAdmin):
    model = Account
    inlines = [StoreAccountInline]

    add_form = AccountCreationForm
    form = AccountChangeForm

    list_display = ("id", "username", "email", "account_type", "is_staff", "is_active")
    search_fields = ("username", "email")
    ordering = ("id",)

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "email", "account_type",
                "store", "admin_email", "permission_flag",
                "password1", "password2", "is_staff", "is_active"
            ),
        }),
    )

    fieldsets = UserAdmin.fieldsets + (
        (_("追加情報"), {"fields": ("account_type",)}),
        (_("店舗情報（店舗アカウント用）"), {"fields": ("store", "admin_email", "permission_flag")}),
    )

    def save_form(self, request, form, change):
        obj = form.save(commit=False)

        # form.cleaned_data から必ず拾ってセット（空ならこの時点でNoneのまま）
        at = form.cleaned_data.get("account_type")
        if at is not None:
            obj.account_type = at

        return obj

    def save_model(self, request, obj, form, change):
        # まず親(Account)を保存
        super().save_model(request, obj, form, change)

        if is_store_type(obj):
         store = form.cleaned_data.get("store")
         admin_email = form.cleaned_data.get("admin_email") or obj.email
         permission_flag = bool(form.cleaned_data.get("permission_flag"))

         if store is None:
                raise ValidationError("店舗アカウントの場合、店舗（store）は必須です。")

         StoreAccount.objects.update_or_create(
                account_ptr=obj,
                defaults={
                    "store": store,
                    "admin_email": admin_email,
                    "permission_flag": permission_flag,
                },
            )
        else:
            # 店舗以外に変えたら StoreAccount を消す（不要ならコメントアウト）
         if hasattr(obj, "storeaccount"):
                obj.storeaccount.delete()

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
    readonly_fields = ("image_preview",)
    fields = ("review", "image_path", "image_preview")

    def image_preview(self, obj):
        if obj and obj.image_path:
            return format_html(
                '<img src="{}" style="height:120px; border:1px solid #ccc;">',
                obj.image_path.url
            )
        return "-"
    image_preview.short_description = "プレビュー"

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
