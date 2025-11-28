from django.contrib import admin
from .models import *

# -------------------------
# 各モデルを管理画面に登録
# -------------------------

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "account_type")
    search_fields = ("username", "email")


@admin.register(CustomerAccount)
class CustomerAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "nickname", "username", "email", "phone_number", "age_group")
    search_fields = ("nickname", "username", "email")


@admin.register(StoreAccount)
class StoreAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "store", "admin_email", "permission_flag")
    search_fields = ("username", "admin_email")


@admin.register(CompanyAccount)
class CompanyAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "company_name", "username", "email")
    search_fields = ("company_name", "username", "email")


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


# -------------------------
# マスタ系モデル
# -------------------------

admin.site.register(AgeGroup)
admin.site.register(Gender)
admin.site.register(AccountType)
admin.site.register(Scene)
admin.site.register(Area)
admin.site.register(ReservationStatus)
admin.site.register(ImageStatus)
admin.site.register(ApplicationStatus)
