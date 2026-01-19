from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth.models import AbstractUser, Group, Permission, BaseUserManager


#----------------
# アカウント
#----------------
class AccountManager(BaseUserManager):
    use_in_migrations = True

    def _get_default_account_type(self):
        """
        createsuperuser / create_user 時に使うデフォルト種別
        なければ自動作成
        """
        return AccountType.objects.get_or_create(
            account_type="管理者"
        )[0]

    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError("username は必須です")

        # ★本丸：account_type を必ず入れる
        if extra_fields.get("account_type") is None:
            extra_fields["account_type"] = self._get_default_account_type()

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(username, email, password, **extra_fields)


class Account(AbstractUser):
    account_type = models.ForeignKey("AccountType", on_delete=models.PROTECT, verbose_name="種類")
    groups = models.ManyToManyField(Group, related_name="account_set", blank=True, verbose_name="グループ", help_text="The groups this user belongs to.")
    user_permissions = models.ManyToManyField(Permission, related_name="account_set", blank=True, verbose_name="ユーザー権限", help_text="Specific permissions for this user.")
    objects = AccountManager() 
    class Meta:
        db_table = "account"; verbose_name = "アカウント"; verbose_name_plural = "アカウント"
    def __str__(self):
        return f"{self.account_type} - {self.username}"

class CustomerAccount(Account):
    nickname = models.CharField(max_length=255, verbose_name="ニックネーム")
    sub_email = models.EmailField(max_length=255, verbose_name="メールアドレス")
    phone_number = models.CharField(max_length=20, verbose_name="電話番号")
    age_group = models.ForeignKey("AgeGroup", on_delete=models.PROTECT, verbose_name="年代")
    address = models.CharField(max_length=255, verbose_name="住所")
    title = models.CharField(max_length=100, verbose_name="タイトル")
    location = models.CharField(max_length=255, verbose_name="現在位置")
    birth_date = models.DateField(verbose_name="生年月日")
    gender = models.ForeignKey("Gender", on_delete=models.PROTECT, verbose_name="性別")
    review_count = models.IntegerField(verbose_name="口コミ数", default=0)
    total_likes = models.IntegerField(verbose_name="総いいね数", default=0)
    standard_score = models.IntegerField(verbose_name="標準点", default=0)
    class Meta:
        db_table = "customer_account"; verbose_name = "顧客アカウント情報"; verbose_name_plural = "顧客アカウント情報"
    def __str__(self):
        return self.nickname

class StoreAccount(Account):
    store = models.ForeignKey("Store", on_delete=models.PROTECT, verbose_name="店舗情報")
    admin_email = models.EmailField(max_length=255, verbose_name="管理者メールアドレス")
    permission_flag = models.BooleanField(verbose_name="権限フラグ", default=False)
    class Meta:
        db_table = "store_account"; verbose_name = "店舗アカウント情報"; verbose_name_plural = "店舗アカウント情報"
    def __str__(self):
        return f"{self.store.store_name} - {self.admin_email}"

class CompanyAccount(Account):
    company_name = models.CharField(max_length=255, verbose_name="企業名")
    class Meta:
        db_table = "company_account"; verbose_name = "企業アカウント情報"; verbose_name_plural = "企業アカウント情報"
    def __str__(self):
        return self.company_name

#----------------
# 店舗
#----------------
class Store(models.Model):
    store_name = models.CharField(max_length=100, verbose_name="店舗名")
    branch_name = models.CharField(max_length=100, verbose_name="支店名")
    email = models.EmailField(max_length=255, verbose_name="メールアドレス")
    phone_number = models.CharField(max_length=20, verbose_name="電話番号")
    address = models.CharField(max_length=255, verbose_name="住所")
    map_location = models.CharField(max_length=255, verbose_name="地図")
    area = models.ForeignKey("Area", on_delete=models.PROTECT, verbose_name="エリア")
    business_hours = models.CharField(max_length=50, verbose_name="営業時間")
    seats = models.IntegerField(verbose_name="席数")
    budget = models.IntegerField(verbose_name="予算")
    scene = models.ForeignKey("Scene", on_delete=models.PROTECT, verbose_name="利用シーン")
    reservable = models.BooleanField(verbose_name="予約可否", default=True)
    editable = models.BooleanField(verbose_name="編集可能", default=True)
    creator = models.ForeignKey("CustomerAccount", on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name="作成者")
    class Meta:
        db_table = "stores"; verbose_name = "店舗基本情報"; verbose_name_plural = "店舗基本情報"
    def __str__(self):
        return f"{self.store_name} - {self.branch_name}"

#----------------
# 口コミ・写真
#----------------
class Review(models.Model):
    reviewer = models.ForeignKey("CustomerAccount", on_delete=models.PROTECT, verbose_name="投稿者")
    store = models.ForeignKey("Store", on_delete=models.PROTECT, verbose_name="店舗")
    score = models.IntegerField(verbose_name="点数")
    review_text = models.TextField(verbose_name="レビュー")
    like_count = models.IntegerField(verbose_name="いいね数", default=0)
    posted_at = models.DateTimeField(auto_now_add=True, verbose_name="投稿日時")
    class Meta:
        db_table = "reviews"; verbose_name = "口コミ"; verbose_name_plural = "口コミ"
    def __str__(self):
        return f"Review by {self.reviewer.nickname} for {self.store.store_name}"

class ReviewPhoto(models.Model):
    review = models.ForeignKey("Review", on_delete=models.CASCADE, related_name="photos", verbose_name="口コミ")
    image_path = models.CharField(max_length=255, verbose_name="画像パス")
    class Meta:
        db_table = "review_photos"; verbose_name = "口コミ写真"; verbose_name_plural = "口コミ写真"
    def __str__(self):
        return self.image_path

class ReviewReport(models.Model):
    review = models.ForeignKey("Review", on_delete=models.CASCADE, verbose_name="口コミ")
    reporter = models.ForeignKey("Account", on_delete=models.CASCADE, verbose_name="通報者")
    report_text = models.TextField(verbose_name="通報内容")
    report_status = models.BooleanField(verbose_name="通報ステータス")
    reported_at = models.DateTimeField(auto_now_add=True, verbose_name="通報日時")
    class Meta:
        db_table = "review_reports"; verbose_name = "通報された口コミ"; verbose_name_plural = "通報された口コミ"
    def __str__(self):
        return f"Report by {self.reporter.username} on Review ID {self.review.id}"

#----------------
# フォロー
#----------------
class Follow(models.Model):
    follower = models.ForeignKey("CustomerAccount", on_delete=models.DO_NOTHING, related_name="follower", verbose_name="フォロー元")
    followee = models.ForeignKey("CustomerAccount", on_delete=models.DO_NOTHING, related_name="followee", verbose_name="フォロー先")
    is_blocked = models.BooleanField(verbose_name="ブロック済み", default=False)
    is_muted = models.BooleanField(verbose_name="ミュート済み", default=False)
    followed_at = models.DateTimeField(auto_now_add=True, verbose_name="フォロー日時")
    class Meta:
        db_table = "follows"; verbose_name = "フォロー"; verbose_name_plural = "フォロー"; unique_together = (("follower", "followee"),)
    def __str__(self):
        return f"{self.follower.nickname} follows {self.followee.nickname}"

#----------------
# 予約者・予約
#----------------
class Reservator(models.Model):
    customer_account = models.ForeignKey("CustomerAccount", on_delete=models.CASCADE, null=True, blank=True, verbose_name="顧客アカウント")
    full_name = models.CharField(max_length=100, verbose_name="氏名")
    full_name_kana = models.CharField(max_length=100, verbose_name="氏名かな")
    email = models.EmailField(max_length=255, verbose_name="メールアドレス")
    phone_number = models.CharField(max_length=20, verbose_name="電話番号")
    class Meta:
        db_table = "reservators"; verbose_name = "予約者情報"; verbose_name_plural = "予約者情報"
    def __str__(self):
        return f"{self.full_name} ({self.email})"

class Reservation(models.Model):
    booking_user = models.ForeignKey("Reservator", on_delete=models.CASCADE, verbose_name="予約者")
    store = models.ForeignKey("Store", on_delete=models.CASCADE, verbose_name="店舗")
    visit_date = models.DateField(verbose_name="来店日")
    visit_time = models.TimeField(verbose_name="来店時刻")
    visit_count = models.IntegerField(verbose_name="来店人数")
    course = models.CharField(max_length=255, verbose_name="コース")
    booking_status = models.ForeignKey("ReservationStatus", on_delete=models.PROTECT, verbose_name="予約ステータス")
    cancel_reason = models.TextField(null=True, blank=True, verbose_name="キャンセル理由")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    class Meta:
        db_table = "reservations"; verbose_name = "予約"; verbose_name_plural = "予約"
    def __str__(self):
        return f"Reservation by {self.booking_user.full_name} at {self.store.store_name} on {self.visit_date}"

class StoreOnlineReservation(models.Model):
    store = models.OneToOneField("Store", on_delete=models.CASCADE, verbose_name="店舗")
    booking_status = models.BooleanField(verbose_name="予約受付状況")
    available_seats = models.IntegerField(verbose_name="予約可能席数")
    date = models.DateField(verbose_name="日付")
    class Meta:
        db_table = "store_online_reservations"; verbose_name = "店舗ネット予約情報"; verbose_name_plural = "店舗ネット予約情報"
    def __str__(self):
        return f"Online Reservation Info for {self.store.store_name} on {self.date}"

#----------------
# 追加モデル：店舗画像・メニュー・申請・ログ・パスワード・仮申請
#----------------
class StoreImage(models.Model):
    store = models.ForeignKey("Store", on_delete=models.CASCADE, verbose_name="店舗")
    image_path = models.CharField(max_length=255, verbose_name="画像パス")
    image_status = models.ForeignKey("ImageStatus", on_delete=models.PROTECT, verbose_name="画像ステータス")
    class Meta:
        db_table = "store_images"; verbose_name = "店舗画像"; verbose_name_plural = "店舗画像"
    def __str__(self):
        return self.image_path

class StoreMenu(models.Model):
    store = models.ForeignKey("Store", on_delete=models.CASCADE, verbose_name="店舗")
    menu_name = models.CharField(max_length=100, verbose_name="メニュー名")
    price = models.IntegerField(verbose_name="価格")
    image_path = models.CharField(max_length=255, verbose_name="メニュー画像パス")
    class Meta:
        db_table = "store_menus"; verbose_name = "メニュー"; verbose_name_plural = "メニュー"
    def __str__(self):
        return self.menu_name

class StoreAccountRequest(models.Model):
    requester = models.ForeignKey("CustomerAccount", on_delete=models.CASCADE, verbose_name="申請者")
    target_store = models.ForeignKey("Store", on_delete=models.CASCADE, verbose_name="対象店舗")
    attachment = models.CharField(max_length=255, verbose_name="添付資料")
    request_status = models.ForeignKey("ApplicationStatus", on_delete=models.PROTECT, verbose_name="申請ステータス")
    store_name = models.CharField(max_length=100, verbose_name="店舗名")
    branch_name = models.CharField(max_length=100, verbose_name="支店名")
    email = models.EmailField(max_length=255, verbose_name="メールアドレス")
    phone_number = models.CharField(max_length=20, verbose_name="電話番号")
    address = models.CharField(max_length=255, verbose_name="住所")
    applicant_name = models.CharField(max_length=100, verbose_name="申込者名")
    relation_to_store = models.CharField(max_length=50, verbose_name="店舗との関係")
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="申請日時")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="承認日時")
    class Meta:
        db_table = "store_account_requests"; verbose_name = "店舗アカウント申請"; verbose_name_plural = "店舗アカウント申請"
    def __str__(self):
        return f"Request by {self.applicant_name} for {self.store_name}"

class StoreAccountRequestLog(models.Model):
    request = models.ForeignKey("StoreAccountRequest", on_delete=models.CASCADE, verbose_name="申請")
    request_status = models.ForeignKey("ApplicationStatus", on_delete=models.PROTECT, verbose_name="申請ステータス")
    comment = models.TextField(verbose_name="コメント")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    class Meta:
        db_table = "store_account_request_logs"; verbose_name = "店舗アカウント申請ログ"; verbose_name_plural = "店舗アカウント申請ログ"
    def __str__(self):
        return f"Log for Request ID {self.request.id} at {self.updated_at}"

class PasswordResetLog(models.Model):
    reset_token = models.CharField(max_length=255, primary_key=True, verbose_name="リセットトークン")
    account = models.ForeignKey("Account", on_delete=models.CASCADE, verbose_name="アカウント")
    expires_at = models.DateTimeField(verbose_name="有効期限")
    used_flag = models.BooleanField(verbose_name="使用済みフラグ", default=False)
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="リセット要求日時")
    class Meta:
        db_table = "password_reset_log"; verbose_name = "パスワードリセットログ"; verbose_name_plural = "パスワードリセットログ"
    def __str__(self):
        return f"Password Reset for {self.account.username} requested at {self.requested_at}"

class TempRequestMailLog(models.Model):
    temp_request_token = models.CharField(max_length=255, primary_key=True, verbose_name="仮申請メールトークン")
    requester = models.ForeignKey("CustomerAccount", on_delete=models.CASCADE, verbose_name="申請者")
    expires_at = models.DateTimeField(verbose_name="有効期限")
    used_flag = models.BooleanField(verbose_name="使用済みフラグ", default=False)
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="要求日時")
    class Meta:
        db_table = "temp_request_mail_log"; verbose_name = "仮申請メールログ"; verbose_name_plural = "仮申請メールログ"
    def __str__(self):
        return f"Temp Request Mail for {self.requester.nickname} requested at {self.requested_at}"

#----------------
# マスタ
#----------------
class AgeGroup(models.Model):
    age_range = models.CharField(max_length=100, verbose_name="年代")
    class Meta:
        db_table = "age_group"; verbose_name = "年代マスタ"; verbose_name_plural = "年代マスタ"
    def __str__(self):
        return self.age_range

class Gender(models.Model):
    gender = models.CharField(max_length=10, verbose_name="性別")
    class Meta:
        db_table = "gender"; verbose_name = "性別マスタ"; verbose_name_plural = "性別マスタ"
    def __str__(self):
        return self.gender

class AccountType(models.Model):
    account_type = models.CharField(max_length=50,unique=True,verbose_name="アカウント種類")
    class Meta:
        db_table = "account_type"; verbose_name = "アカウント種類マスタ"; verbose_name_plural = "アカウント種類マスタ"
    def __str__(self):
        return self.account_type

class Scene(models.Model):
    scene_name = models.CharField(max_length=100, verbose_name="シーン名")
    class Meta:
        db_table = "scene"; verbose_name = "利用シーン"; verbose_name_plural = "利用シーン"
    def __str__(self):
        return self.scene_name

class Area(models.Model):
    area_name = models.CharField(max_length=100, verbose_name="エリア名")
    class Meta:
        db_table = "area"; verbose_name = "エリア"; verbose_name_plural = "エリア"
    def __str__(self):
        return self.area_name

class ReservationStatus(models.Model):
    status = models.CharField(max_length=50, verbose_name="予約ステータス")
    class Meta:
        db_table = "reservation_statuses"; verbose_name = "予約ステータスマスタ"; verbose_name_plural = "予約ステータスマスタ"
    def __str__(self):
        return self.status

class ImageStatus(models.Model):
    status = models.CharField(max_length=10, verbose_name="画像ステータス")
    class Meta:
        db_table = "image_statuses"; verbose_name = "画像ステータスマスタ"; verbose_name_plural = "画像ステータスマスタ"
    def __str__(self):
        return self.status

class ApplicationStatus(models.Model):
    status = models.CharField(max_length=50, verbose_name="ステータス")
    class Meta:
        db_table = "application_statuses"; verbose_name = "申請ステータスマスタ"; verbose_name_plural = "申請ステータスマスタ"
    def __str__(self):
        return self.status

