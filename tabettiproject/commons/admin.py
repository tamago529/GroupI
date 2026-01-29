from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.html import format_html
from django.core.exceptions import ValidationError

from .models import (
    Account, CustomerAccount, StoreAccount, CompanyAccount,
    Store, AccountType, Area, Scene, Gender, AgeGroup,
    ReservationStatus, ImageStatus, ApplicationStatus,
    Review, ReviewPhoto, ReviewReport, Follow, Reservator,
    Reservation, StoreOnlineReservation, StoreImage, StoreMenu,
    StoreAccountRequest, StoreAccountRequestLog, PasswordResetLog, TempRequestMailLog, StoreInfoReport,
    StoreAccessLog
)
from commons.constants import GENRE_CHOICES

# ==========================================================
# 1. 作成用フォーム（ここがエラー回避の核心）
# ==========================================================

# --- StoreAccountCreationForm の修正 ---
class StoreAccountCreationForm(UserCreationForm):
    """
    UserCreationFormを継承しつつ、
    Metaクラスを正しく設定してパスワード2回入力を有効にします
    """
    class Meta:
        model = StoreAccount
        # ここに 'password' は含めません（UserCreationFormが自動で出すため）
        fields = ("username", "account_type", "email", "store", "admin_email", "permission_flag")

    def save(self, commit=True):
        user = super().save(commit=False)
        # 🌟ここで account_type を強制的にセット（IntegrityError対策）
        user.account_type = self.cleaned_data.get("account_type")
        if commit:
            user.save()
        return user

class CustomerAccountCreationForm(UserCreationForm):
    """顧客アカウント作成専用フォーム"""
    class Meta:
        model = CustomerAccount
        # パスワード以外で作成時に表示したいフィールドを列挙
        fields = ("username", "account_type", "email", "nickname", "phone_number", "age_group", "gender", "birth_date")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("メールアドレスは必須です。")
        if Account.objects.filter(email__iexact=email).exists():
            raise ValidationError("このメールアドレスは既に使用されています。")
        return email


    def save(self, commit=True):
        user = super().save(commit=False)
        user.account_type = self.cleaned_data.get("account_type")
        if commit:
            user.save()
        return user

class CompanyAccountCreationForm(UserCreationForm):
    """企業アカウント作成専用フォーム"""
    class Meta:
        model = CompanyAccount
        fields = ("username", "account_type", "email", "company_name")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.account_type = self.cleaned_data.get("account_type")
        if commit:
            user.save()
        return user
# ==========================================================
# 2. アカウント管理（各Adminクラスの設定）
# ==========================================================

# --- 親Account：管理用（ここからは追加させない） ---
@admin.register(Account)
class AccountAdmin(UserAdmin):
    list_display = ('id', 'username', 'account_type', 'is_staff')
    def has_add_permission(self, request): return False

# --- 店舗アカウント管理 ---
# --- StoreAccountAdmin の修正 ---
@admin.register(StoreAccount)
class StoreAccountAdmin(UserAdmin):
    add_form = StoreAccountCreationForm
    form = UserChangeForm # 編集用は標準でOK

    list_display = ('id', 'username', 'store', 'account_type')

    readonly_fields = UserAdmin.readonly_fields + ("store_info_reports",)

    def store_info_reports(self, obj):
        if not obj or not obj.store_id:
            return "-"

        qs = StoreInfoReport.objects.filter(store=obj.store).order_by("-created_at")[:20]
        if not qs.exists():
            return "報告はありません。"

        lines = []
        for r in qs:
            reporter = r.reporter.nickname if r.reporter else "-"
            text = r.message.replace("\n", " ")
            if len(text) > 80:
                text = text[:80] + "…"
            lines.append(f"{r.created_at:%Y/%m/%d %H:%M} / {reporter} / {text}")
        return "\n".join(lines)

    store_info_reports.short_description = "店舗情報の報告（最新20件）"

    # 🌟作成画面のレイアウトを修正（password1, password2が出るようにする）
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'account_type', 'email', 'store', 'admin_email', 'permission_flag'),
        }),
        # ここを追加することで、Django標準の「パスワード2回入力」が表示されます
        ('パスワード設定', {
            'fields': ('password1', 'password2'),
        }),
    )

    # 編集画面のレイアウト
    fieldsets = UserAdmin.fieldsets + (
        ('店舗詳細情報', {'fields': ('store', 'admin_email', 'permission_flag', 'account_type', 'store_info_reports')}),
    )
    

# --- 顧客アカウント管理 ---
@admin.register(CustomerAccount)
class CustomerAccountAdmin(UserAdmin):
    add_form = CustomerAccountCreationForm # 🌟専用フォームを指定
    list_display = ('id', 'username', 'nickname', 'account_type')
    
    # 🌟作成画面のレイアウト
    def inquiry_short(self, obj):
        if not obj.inquiry_log:
            return "-"
        return (obj.inquiry_log[:40] + "…") if len(obj.inquiry_log) > 40 else obj.inquiry_log
    inquiry_short.short_description = "問い合わせ(最新抜粋)"

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'account_type', 'email', 'nickname', 'phone_number', 'age_group', 'gender', 'birth_date'),
        }),
        ('パスワード設定', {'fields': ('password1', 'password2')}),
    )
    # 編集画面のレイアウト
    fieldsets = UserAdmin.fieldsets + (
        ('顧客詳細情報', {'fields': ('nickname', 'phone_number', 'age_group', 'gender', 'birth_date', 'account_type', 'inquiry_log')}),
    )

# --- 企業アカウント管理 ---
@admin.register(CompanyAccount)
class CompanyAccountAdmin(UserAdmin):
    add_form = CompanyAccountCreationForm # 🌟専用フォームを指定
    list_display = ('id', 'username', 'company_name', 'account_type')
    
    # 🌟作成画面のレイアウト
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'account_type', 'email', 'company_name'),
        }),
        ('パスワード設定', {'fields': ('password1', 'password2')}),
    )
    # 編集画面のレイアウト
    fieldsets = UserAdmin.fieldsets + (
        ('企業詳細情報', {'fields': ('company_name', 'account_type')}),
    )

# ==========================================================
# 3. 通常モデルの登録（変更なし）
# ==========================================================
@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("id", "store_name", "branch_name")
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "genre":
            kwargs["widget"] = forms.Select(choices=GENRE_CHOICES)
        return super().formfield_for_dbfield(db_field, **kwargs)


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


@admin.register(StoreAccessLog)
class StoreAccessLogAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "accessed_at")
    list_filter = ("store", "accessed_at")
    date_hierarchy = "accessed_at"
