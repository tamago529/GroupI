from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from datetime import time


# ----------------
# マスタ
# ----------------
class AgeGroup(models.Model):
    age_range = models.CharField(max_length=100, verbose_name="年代")

    class Meta:
        db_table = "age_group"
        verbose_name = "年代マスタ"
        verbose_name_plural = "年代マスタ"

    def __str__(self):
        return self.age_range


class Gender(models.Model):
    gender = models.CharField(max_length=10, verbose_name="性別")

    class Meta:
        db_table = "gender"
        verbose_name = "性別マスタ"
        verbose_name_plural = "性別マスタ"

    def __str__(self):
        return self.gender


class AccountType(models.Model):
    account_type = models.CharField(max_length=50, unique=True, verbose_name="アカウント種類")

    class Meta:
        db_table = "account_type"
        verbose_name = "アカウント種類マスタ"
        verbose_name_plural = "アカウント種類マスタ"

    def __str__(self):
        return self.account_type


class Scene(models.Model):
    scene_name = models.CharField(max_length=100, unique=True, verbose_name="シーン名")

    class Meta:
        db_table = "scene"
        verbose_name = "利用シーン"
        verbose_name_plural = "利用シーン"

    def __str__(self):
        return self.scene_name


class Area(models.Model):
    area_name = models.CharField(max_length=100, verbose_name="エリア名")

    class Meta:
        db_table = "area"
        verbose_name = "エリア"
        verbose_name_plural = "エリア"

    def __str__(self):
        return self.area_name


class ReservationStatus(models.Model):
    status = models.CharField(max_length=50, verbose_name="予約ステータス")

    class Meta:
        db_table = "reservation_statuses"
        verbose_name = "予約ステータスマスタ"
        verbose_name_plural = "予約ステータスマスタ"

    def __str__(self):
        return self.status


class ImageStatus(models.Model):
    status = models.CharField(max_length=10, verbose_name="画像ステータス")

    class Meta:
        db_table = "image_statuses"
        verbose_name = "画像ステータスマスタ"
        verbose_name_plural = "画像ステータスマスタ"

    def __str__(self):
        return self.status


class ApplicationStatus(models.Model):
    status = models.CharField(max_length=50, verbose_name="ステータス")

    class Meta:
        db_table = "application_statuses"
        verbose_name = "申請ステータスマスタ"
        verbose_name_plural = "申請ステータスマスタ"

    def __str__(self):
        return self.status


# ----------------
# アカウント
# ----------------
class AccountManager(BaseUserManager):
    use_in_migrations = True

    def _get_default_account_type(self):
        """
        createsuperuser / create_user 時に使うデフォルト種別
        なければ自動作成
        """
        return AccountType.objects.get_or_create(account_type="管理者")[0]

    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError("username は必須です")

        # account_type を必ず入れる
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
    email = models.EmailField(max_length=254, unique=True, verbose_name="メールアドレス")  # ✅ 追加/上書き
    account_type = models.ForeignKey("AccountType", on_delete=models.PROTECT, verbose_name="種類")
    objects = AccountManager()

    class Meta:
        db_table = "account"
        verbose_name = "アカウント"
        verbose_name_plural = "アカウント"

    def __str__(self):
        return f"{self.account_type} - {self.username}"


class CustomerAccount(Account):
    nickname = models.CharField(max_length=255, verbose_name="ニックネーム")
    sub_email = models.EmailField(max_length=255, verbose_name="メールアドレス")
    phone_number = models.CharField(max_length=20, verbose_name="電話番号")
    age_group = models.ForeignKey("AgeGroup", on_delete=models.PROTECT, verbose_name="年代")
    address = models.CharField(max_length=255, verbose_name="住所")
    title = models.CharField(max_length=100, verbose_name="タイトル")
    birth_date = models.DateField(verbose_name="生年月日")
    first_name_kana = models.CharField(max_length=100, verbose_name="めい", blank=True, default="")
    last_name_kana = models.CharField(max_length=100, verbose_name="せい", blank=True, default="")
    occupation = models.CharField(max_length=100, verbose_name="職業", blank=True, default="")
    camera = models.CharField(max_length=100, verbose_name="使っているカメラ", blank=True, default="")
    introduction = models.TextField(verbose_name="自己紹介", blank=True, default="")
    subtitle = models.CharField(max_length=255, verbose_name="サブタイトル", blank=True, default="")
    genre_focus = models.TextField(verbose_name="得意ジャンル・こだわり", blank=True, default="")
    gender = models.ForeignKey("Gender", on_delete=models.PROTECT, verbose_name="性別")
    review_count = models.IntegerField(verbose_name="口コミ数", default=0)
    total_likes = models.IntegerField(verbose_name="総いいね数", default=0)
    standard_score = models.IntegerField(verbose_name="標準点", default=0)
    trust_score = models.FloatField(verbose_name="信頼度スコア", default=50.0)
    inquiry_log = models.TextField(verbose_name="問い合わせ内容", blank=True, default="")
    icon_image = models.ImageField(
        upload_to="customer/icon/",
        null=True,
        blank=True,
        default="customer/icon/default_cover.jpg",
        verbose_name="アイコン画像",
    )
    cover_image = models.ImageField(
        upload_to="customer/cover/",
        null=True,
        blank=True,
        default="customer/cover/default_cover.jpg",
        verbose_name="カバー画像",
    )

    class Meta:
        db_table = "customer_account"
        verbose_name = "顧客アカウント情報"
        verbose_name_plural = "顧客アカウント情報"

    def __str__(self):
        return self.nickname

    def calculate_trust_score(self):
        """
        ユーザーの信頼度スコアを計算 (0-100点)
        
        計算要素:
        - アカウント年齢 (0-25点)
        - レビュー数 (0-25点)
        - レビューの質 (0-30点)
        - レビューの一貫性 (0-20点)
        """
        from datetime import datetime
        from django.db.models import Avg, StdDev
        
        score = 0.0
        
        # 1. アカウント年齢スコア (0-25点)
        if self.date_joined:
            account_age_days = (datetime.now(self.date_joined.tzinfo) - self.date_joined).days
            # 365日以上で満点、線形に増加
            age_score = min(25.0, (account_age_days / 365.0) * 25.0)
            score += age_score
        
        # 2. レビュー数スコア (0-25点)
        # 50件以上で満点、線形に増加
        review_score = min(25.0, (self.review_count / 50.0) * 25.0)
        score += review_score
        
        # 3. レビューの質スコア (0-30点)
        if self.review_count > 0:
            # 平均いいね数を計算
            avg_likes = self.total_likes / self.review_count
            # 平均10いいね以上で満点、線形に増加
            quality_score = min(30.0, (avg_likes / 10.0) * 30.0)
            score += quality_score
        
        # 4. レビューの一貫性スコア (0-20点)
        reviews = self.review_set.all()
        if reviews.count() >= 3:
            # 評価点数の標準偏差を計算
            stats = reviews.aggregate(std_dev=StdDev('score'))
            std_dev = stats['std_dev'] or 0
            
            # 標準偏差が小さいほど一貫性が高い
            # 標準偏差0で満点、2.0以上で0点
            consistency_score = max(0.0, 20.0 - (std_dev / 2.0) * 20.0)
            score += consistency_score
        elif reviews.count() > 0:
            # レビュー数が少ない場合は中間点
            score += 10.0
        
        return round(score, 2)

    def update_trust_score(self):
        """信頼度スコアを計算して保存"""
        self.trust_score = self.calculate_trust_score()
        self.save(update_fields=['trust_score'])



class Store(models.Model):
    store_name = models.CharField(max_length=100, verbose_name="店舗名")
    branch_name = models.CharField(max_length=100, verbose_name="支店名")
    email = models.EmailField(max_length=255, verbose_name="メールアドレス")
    phone_number = models.CharField(max_length=20, verbose_name="電話番号")
    address = models.CharField(max_length=255, verbose_name="住所")
    map_location = models.CharField(max_length=255, verbose_name="地図")
    area = models.ForeignKey("Area", on_delete=models.PROTECT, verbose_name="エリア")
    business_hours = models.CharField(max_length=50, verbose_name="営業時間")

    # 営業時間（1枠目）
    open_time_1 = models.TimeField(
        null=True, blank=True, verbose_name="開店時間①"
    )
    close_time_1 = models.TimeField(
        null=True, blank=True, verbose_name="閉店時間①"
    )

    # 営業時間（2枠目：ランチ・ディナー想定）
    open_time_2 = models.TimeField(
        null=True, blank=True, verbose_name="開店時間②"
    )
    close_time_2 = models.TimeField(
        null=True, blank=True, verbose_name="閉店時間②"
    )

    seats = models.IntegerField(verbose_name="席数")
    budget = models.IntegerField(verbose_name="予算")
    genre = models.CharField(max_length=100, verbose_name="ジャンル")
    scene = models.ForeignKey("Scene", on_delete=models.PROTECT, verbose_name="利用シーン")
    reservable = models.BooleanField(verbose_name="予約可否", default=True)
    editable = models.BooleanField(verbose_name="編集可能", default=True)
    creator = models.ForeignKey("CustomerAccount", on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name="作成者")

    class Meta:
        db_table = "stores"
        verbose_name = "店舗基本情報"
        verbose_name_plural = "店舗基本情報"

    def __str__(self):
        return f"{self.store_name} - {self.branch_name}"


class StoreAccount(Account):
    store = models.ForeignKey("Store", on_delete=models.PROTECT, verbose_name="店舗情報")
    admin_email = models.EmailField(max_length=255, verbose_name="管理者メールアドレス")
    permission_flag = models.BooleanField(verbose_name="権限フラグ", default=False)

    class Meta:
        db_table = "store_account"
        verbose_name = "店舗アカウント情報"
        verbose_name_plural = "店舗アカウント情報"

    def __str__(self):
        return f"{self.store.store_name} - {self.admin_email}"


class CompanyAccount(Account):
    company_name = models.CharField(max_length=255, verbose_name="企業名")

    class Meta:
        db_table = "company_account"
        verbose_name = "企業アカウント情報"
        verbose_name_plural = "企業アカウント情報"

    def __str__(self):
        return self.company_name


# ----------------
# 口コミ・写真
# ----------------
class Review(models.Model):
    reviewer = models.ForeignKey("CustomerAccount", on_delete=models.PROTECT, verbose_name="投稿者")
    store = models.ForeignKey("Store", on_delete=models.PROTECT, verbose_name="店舗")
    score = models.IntegerField(verbose_name="点数")
    review_text = models.TextField(verbose_name="レビュー")
    like_count = models.IntegerField(verbose_name="いいね数", default=0)
    liked_users = models.ManyToManyField(
        "Account", 
        related_name="liked_reviews", 
        blank=True, 
        verbose_name="いいねしたユーザー"
    )
    posted_at = models.DateTimeField(auto_now_add=True, verbose_name="投稿日時")
    
    class Meta:
        db_table = "reviews"
        verbose_name = "口コミ"
        verbose_name_plural = "口コミ"

    def __str__(self):
        return f"Review by {self.reviewer.nickname} for {self.store.store_name}"


class ReviewPhoto(models.Model):
    review = models.ForeignKey("Review", on_delete=models.CASCADE, related_name="photos", verbose_name="口コミ")
    image_path = models.ImageField(upload_to="review/photos/", verbose_name="画像")

    class Meta:
        db_table = "review_photos"
        verbose_name = "口コミ写真"
        verbose_name_plural = "口コミ写真"

    def __str__(self):
        return str(self.image_path)


class ReviewReport(models.Model):
    review = models.ForeignKey("Review", on_delete=models.CASCADE, verbose_name="口コミ")
    reporter = models.ForeignKey("Account", on_delete=models.CASCADE, verbose_name="通報者")
    report_text = models.TextField(verbose_name="通報内容")
    report_status = models.BooleanField(verbose_name="通報ステータス")
    reported_at = models.DateTimeField(auto_now_add=True, verbose_name="通報日時")

    class Meta:
        db_table = "review_reports"
        verbose_name = "通報された口コミ"
        verbose_name_plural = "通報された口コミ"

    def __str__(self):
        return f"Report by {self.reporter.username} on Review ID {self.review.id}"


# ----------------
# フォロー
# ----------------
class Follow(models.Model):
    follower = models.ForeignKey("CustomerAccount", on_delete=models.DO_NOTHING, related_name="follower", verbose_name="フォロー元")
    followee = models.ForeignKey("CustomerAccount", on_delete=models.DO_NOTHING, related_name="followee", verbose_name="フォロー先")
    is_blocked = models.BooleanField(verbose_name="ブロック済み", default=False)
    is_muted = models.BooleanField(verbose_name="ミュート済み", default=False)
    followed_at = models.DateTimeField(auto_now_add=True, verbose_name="フォロー日時")

    class Meta:
        db_table = "follows"
        verbose_name = "フォロー"
        verbose_name_plural = "フォロー"
        unique_together = (("follower", "followee"),)

    def __str__(self):
        return f"{self.follower.nickname} follows {self.followee.nickname}"


# ----------------
# 予約者・予約
# ----------------
class Reservator(models.Model):
    customer_account = models.ForeignKey("CustomerAccount", on_delete=models.CASCADE, null=True, blank=True, verbose_name="顧客アカウント")
    full_name = models.CharField(max_length=100, verbose_name="氏名")
    full_name_kana = models.CharField(max_length=100, verbose_name="氏名かな")
    email = models.EmailField(max_length=255, verbose_name="メールアドレス")
    phone_number = models.CharField(max_length=20, verbose_name="電話番号")

    class Meta:
        db_table = "reservators"
        verbose_name = "予約者情報"
        verbose_name_plural = "予約者情報"

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class Reservation(models.Model):
    booking_user = models.ForeignKey("Reservator", on_delete=models.CASCADE, verbose_name="予約者")
    store = models.ForeignKey("Store", on_delete=models.CASCADE, verbose_name="店舗")
    visit_date = models.DateField(verbose_name="来店日")
    visit_time = models.TimeField(verbose_name="来店時刻")

    start_time = models.TimeField(
        null=True, blank=True, verbose_name="来店開始時刻"
    )
    end_time = models.TimeField(
        null=True, blank=True, verbose_name="来店終了時刻"
    )

    visit_count = models.IntegerField(verbose_name="来店人数")
    course = models.CharField(max_length=255, verbose_name="コース")
    booking_status = models.ForeignKey("ReservationStatus", on_delete=models.PROTECT, verbose_name="予約ステータス")
    cancel_reason = models.TextField(null=True, blank=True, verbose_name="キャンセル理由")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = "reservations"
        verbose_name = "予約"
        verbose_name_plural = "予約"

    def __str__(self):
        return f"Reservation by {self.booking_user.full_name} at {self.store.store_name} on {self.visit_date}"


class StoreOnlineReservation(models.Model):
    store = models.ForeignKey("Store", on_delete=models.CASCADE, verbose_name="店舗")
    date = models.DateField(verbose_name="日付")
    booking_status = models.BooleanField(verbose_name="予約受付状況", default=True)
    available_seats = models.IntegerField(verbose_name="予約可能席数", default=0)

    class Meta:
        db_table = "store_online_reservations"
        verbose_name = "店舗ネット予約情報"
        verbose_name_plural = "店舗ネット予約情報"
        constraints = [
            models.UniqueConstraint(
                fields=["store", "date"],
                name="uniq_store_date"
            )
        ]

    def __str__(self):
        return f"{self.store.store_name} - {self.date}"


# ----------------
# 追加モデル：店舗画像・メニュー・申請・ログ・パスワード・仮申請
# ----------------
class StoreImage(models.Model):
    store = models.ForeignKey(
        "Store",
        on_delete=models.CASCADE,
        verbose_name="店舗",
        related_name="images",
    )

    # 旧：パス文字列（static等）を保持したい場合のため残す
    image_path = models.CharField(
        max_length=255,
        verbose_name="画像パス（旧）",
        blank=True,
        default="",
    )

    # 新：アップロード画像を保持（media配下に保存される）
    image_file = models.ImageField(
        upload_to="store/images/",
        verbose_name="画像ファイル（新）",
        null=True,
        blank=True,
    )

    image_status = models.ForeignKey(
        "ImageStatus",
        on_delete=models.PROTECT,
        verbose_name="画像ステータス",
    )

    class Meta:
        db_table = "store_images"
        verbose_name = "店舗画像"
        verbose_name_plural = "店舗画像"

    def __str__(self):
        # 新があれば新、なければ旧
        if self.image_file:
            return str(self.image_file)
        return self.image_path


class StoreMenu(models.Model):
    store = models.ForeignKey(
        "Store",
        on_delete=models.CASCADE,
        verbose_name="店舗",
        related_name="menus",
    )
    menu_name = models.CharField(max_length=100, verbose_name="メニュー名")
    price = models.IntegerField(verbose_name="価格")

    # 旧：パス文字列（static等）を保持したい場合のため残す
    image_path = models.CharField(
        max_length=255,
        verbose_name="メニュー画像パス（旧）",
        blank=True,
        default="",
    )

    # 新：アップロード画像を保持
    image_file = models.ImageField(
        upload_to="store/menus/",
        verbose_name="メニュー画像ファイル（新）",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "store_menus"
        verbose_name = "メニュー"
        verbose_name_plural = "メニュー"

    def __str__(self):
        return self.menu_name



class StoreAccountRequest(models.Model):
    requester = models.ForeignKey("CustomerAccount", on_delete=models.CASCADE, verbose_name="申請者")
    target_store = models.ForeignKey("Store", on_delete=models.CASCADE, verbose_name="対象店舗")
    license_image = models.ImageField(upload_to="store_account_requests/licenses/",null=True,blank=True,verbose_name="営業許可証")
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
        db_table = "store_account_requests"
        verbose_name = "店舗アカウント申請"
        verbose_name_plural = "店舗アカウント申請"

    def __str__(self):
        return f"Request by {self.applicant_name} for {self.store_name}"


class StoreAccountRequestLog(models.Model):
    request = models.ForeignKey("StoreAccountRequest", on_delete=models.CASCADE, verbose_name="申請")
    request_status = models.ForeignKey("ApplicationStatus", on_delete=models.PROTECT, verbose_name="申請ステータス")
    comment = models.TextField(verbose_name="コメント")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "store_account_request_logs"
        verbose_name = "店舗アカウント申請ログ"
        verbose_name_plural = "店舗アカウント申請ログ"

    def __str__(self):
        return f"Log for Request ID {self.request.id} at {self.updated_at}"


class PasswordResetLog(models.Model):
    reset_token = models.CharField(max_length=255, primary_key=True, verbose_name="リセットトークン")
    account = models.ForeignKey("Account", on_delete=models.CASCADE, verbose_name="アカウント")
    expires_at = models.DateTimeField(verbose_name="有効期限")
    used_flag = models.BooleanField(verbose_name="使用済みフラグ", default=False)
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="リセット要求日時")

    class Meta:
        db_table = "password_reset_log"
        verbose_name = "パスワードリセットログ"
        verbose_name_plural = "パスワードリセットログ"

    def __str__(self):
        return f"Password Reset for {self.account.username} requested at {self.requested_at}"


class TempRequestMailLog(models.Model):
    temp_request_token = models.CharField(max_length=255, primary_key=True, verbose_name="仮申請メールトークン")
    requester = models.ForeignKey("CustomerAccount", on_delete=models.CASCADE, verbose_name="申請者")
    expires_at = models.DateTimeField(verbose_name="有効期限")
    used_flag = models.BooleanField(verbose_name="使用済みフラグ", default=False)
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="要求日時")

    class Meta:
        db_table = "temp_request_mail_log"
        verbose_name = "仮申請メールログ"
        verbose_name_plural = "仮申請メールログ"

    def __str__(self):
        return f"Temp Request Mail for {self.requester.nickname} requested at {self.requested_at}"

class StoreInfoReport(models.Model):
    store = models.ForeignKey(
        "Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="対象店舗",
    )
    reporter = models.ForeignKey(
        "CustomerAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="報告者",
    )
    message = models.TextField(verbose_name="報告内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="報告日時")

    class Meta:
        db_table = "store_info_reports"
        verbose_name = "店舗情報の報告"
        verbose_name_plural = "店舗情報の報告"
        ordering = ["-created_at"]

    def __str__(self):
        return f"store={self.store_id} reporter={self.reporter_id} {self.created_at}"


class StoreInfoReportPhoto(models.Model):
    report = models.ForeignKey(
        "StoreInfoReport",
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="報告",
    )
    image = models.ImageField(upload_to="store_reports/photos/", verbose_name="写真")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="アップロード日時")

    class Meta:
        db_table = "store_info_report_photos"
        verbose_name = "店舗情報報告の写真"
        verbose_name_plural = "店舗情報報告の写真"

    def __str__(self):
        return str(self.image)


class StoreAccessLog(models.Model):
    store = models.ForeignKey(
        "Store",
        on_delete=models.CASCADE,
        related_name="access_logs",
        verbose_name="店舗",
    )
    accessed_at = models.DateTimeField(auto_now_add=True, verbose_name="アクセス日時")

    class Meta:
        db_table = "store_access_logs"
        verbose_name = "店舗アクセスログ"
        verbose_name_plural = "店舗アクセスログ"
        ordering = ["-accessed_at"]

    def __str__(self):
        return f"{self.store.store_name} - {self.accessed_at}"