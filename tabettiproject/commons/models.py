from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser




#----------------
#アカウント
#----------------
class Account(AbstractUser):
    """			
    種類 account_type_id FK->account_type
    ログインID login_id
    パスワードハッシュ password_hash
    """
    account_type_id = models.ForeignKey(
        "AccountType",
        on_delete=models.PROTECT,
        db_column="account_type_id",
        verbose_name="種類",
    )

    class Meta:
        db_table = "account"
        verbose_name = "アカウント"
        verbose_name_plural = "アカウント"
    def __str__(self):
        return f"{self.account_type.name} - {self.login_id}"
    

#----------------
#顧客アカウント情報
#----------------
class Customer_Account(Account):
    """			
    アカウントID account_id PK.FK->account
    ニックネーム nickname
    メールアドレス email								
    電話番号 phone_number								
    年代 age_group_id								
    住所 address								
    タイトル title								
    現在位置 location								
    生年月日 birth_date								
    性別 gender_id								
    口コミ数 review_count								
    総いいね数 total_likes								
    標準点 standard_score
    """
    account_id = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        db_column="account_id",
        primary_key=True,
        verbose_name="アカウントID",
    )
    nickname = models.CharField(
        max_length=255,
        verbose_name="ニックネーム",
    )
    email = models.EmailField(
        max_length=255,
        verbose_name="メールアドレス",
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name="電話番号",
    )
    age_group_id = models.ForeignKey(
        "Age_Group",
        on_delete=models.PROTECT,
        db_column="age_group_id",
        verbose_name="年代",
    )
    address = models.CharField(
        max_length=255,
        verbose_name="住所",
    )
    title = models.CharField(
        max_length=100,
        verbose_name="タイトル",
    )
    location = models.CharField(
        max_length=255,
        verbose_name="現在位置",
    )
    birth_date = models.DateField(
        verbose_name="生年月日",
    )
    gender_id = models.ForeignKey(
        "Gender",
        on_delete=models.PROTECT,
        db_column="gender_id",
        verbose_name="性別",
    )
    review_count = models.IntegerField(
        verbose_name="口コミ数",
    )
    total_likes = models.IntegerField(
        verbose_name="総いいね数",
    )
    standard_score = models.ImageField(
        verbose_name="標準点",
    )
    class Meta:
        db_table = "customer_account"
        verbose_name = "顧客アカウント情報"
        verbose_name_plural = "顧客アカウント情報"
    def __str__(self):
        return f"{self.nickname}"
#----------------
#店舗アカウント情報
#----------------
class Store_Account(Account):
    """
    アカウントID account_id								
    店舗情報ID store_id								
    管理者メールアドレス admin_email								
    権限フラグ permission_flag								
    """
    account_id = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        db_column="account_id",
        primary_key=True,
        verbose_name="アカウントID",
    )
    store_id = models.ForeignKey(
        "Stores",
        on_delete=models.PROTECT,
        db_column="store_id",
        verbose_name="店舗情報ID",
    )
    admin_email = models.EmailField(
        max_length=255,
        verbose_name="管理者メールアドレス",
    )
    permission_flag = models.BooleanField(
        verbose_name="権限フラグ",
    )
    class Meta:
        db_table = "store_account"
        verbose_name = "店舗アカウント情報"
        verbose_name_plural = "店舗アカウント情報"
    def __str__(self):
        return f"{self.store.name} - {self.admin_email}"
#----------------
#企業アカウント情報
#----------------
class Company_Account(Account):
    """
    アカウントID account_id
    企業名 company_name
    """
    account_id = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        db_column="account_id",
        primary_key=True,
        verbose_name="アカウントID",
    )
    company_name = models.CharField(
        max_length=255,
        verbose_name="企業名",
    )
    class Meta:
        db_table = "company_account"
        verbose_name = "企業アカウント情報"
        verbose_name_plural = "企業アカウント情報"
    def __str__(self):
        return f"{self.company_name}"
#----------------
#店舗基本情報
#----------------
class Stores(models.Model):
    """
    店舗名 store_name								
    支店名 branch_name								
    メールアドレス email								
    電話番号 phone_number								
    住所 address								
    地図 map_location								
    エリア area_id								
    営業時間 business_hours								
    席数 seats								
    予算 budget								
    利用シーン scene_id								
    予約可否 reservable								
    編集可能 editable								
    作成者ID creator_id								
    """
    store_name = models.CharField(
        max_length=100,
        verbose_name="店舗名",
    )
    branch_name = models.CharField(
        max_length=100,
        verbose_name="支店名",
    )
    email = models.EmailField(
        max_length=255,
        verbose_name="メールアドレス",
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name="電話番号",
    )
    address = models.GeometryField(
        verbose_name="住所",
    )
    map_location = models.CharField(
        max_length=255,
        verbose_name="地図",
    )
    area_id = models.ForeignKey(
        "Area",
        on_delete=models.PROTECT,
        db_column="area_id",
        verbose_name="エリア",
    )
    business_hours = models.CharField(
        max_length=50,
        verbose_name="営業時間",
    )
    seats = models.IntegerField(
        verbose_name="席数",
    )
    budget = models.IntegerField(
        verbose_name="予算",
    )
    scene_id = models.ForeignKey(
        "Scene",
        on_delete=models.PROTECT,
        db_column="scene_id",
        verbose_name="利用シーン",
    )
    reservable = models.BooleanField(
        verbose_name="予約可否",
    )
    editable = models.BooleanField(
        verbose_name="編集可能",
    )
    creator_id = models.ForeignKey(
        "Customer_Account",
        on_delete=models.DO_NOTHING,
        db_column="creator_id",
        verbose_name="作成者ID",
    )
    class Meta:
        db_table = "stores"
        verbose_name = "店舗基本情報"
        verbose_name_plural = "店舗基本情報"
    def __str__(self):
        return f"{self.store_name} - {self.branch_name}"
#----------------
#店舗アカウント申請
#----------------
class Store_Account_requests(models.Model):
    """
    申請者ID requester_id								
    対象店舗ID target_store_id								
    添付資料 attachment								
    申請ステータス request_status								
    店舗名 store_name								
    支店名 branch_name								
    メールアドレス email								
    電話番号 phone_number								
    住所 address								
    申込者名 applicant_name								
    店舗との関係 relation_to_store								
    申請日時 requested_at								
    承認日時 approved_at								
    """
    requester_id = models.ForeignKey(
        "Customer_Account",
        on_delete=models.CASCADE,
        db_column="requester_id",
        verbose_name="申請者ID",
    )
    target_store_id = models.ForeignKey(
        "Stores",
        on_delete=models.CASCADE,
        db_column="target_store_id",
        verbose_name="対象店舗ID",
    )
    attachment = models.CharField(
        max_length=255,
        verbose_name="添付資料",
    )
    request_status = models.ForeignKey(
        "Application_Statuses",
        on_delete=models.PROTECT,
        db_column="request_status",
        verbose_name="申請ステータス",
    )
    store_name = models.CharField(
        max_length=100,
        verbose_name="店舗名",
    )
    branch_name = models.CharField(
        max_length=100,
        verbose_name="支店名",
    )
    email = models.EmailField(
        max_length=255,
        verbose_name="メールアドレス",
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name="電話番号",
    )
    address = models.CharField(
        max_length=255,
        verbose_name="住所",
    )
    applicant_name = models.CharField(
        max_length=100,
        verbose_name="申込者名",
    )
    relation_to_store = models.CharField(
        max_length=50,
        verbose_name="店舗との関係",
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="申請日時",
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="承認日時",
    )
    class Meta:
        db_table = "store_account_requests"
        verbose_name = "店舗アカウント申請"
        verbose_name_plural = "店舗アカウント申請"
    def __str__(self):
        return f"Request by {self.applicant_name} for {self.store_name}"
#----------------
#店舗アカウント申請ログ
#----------------
class Store_Account_request_logs(models.Model):
    """
    申請ID request_id								
    申請ステータス request_status								
    コメント comment								
    更新日時 updated_at								
    """
    request_id = models.ForeignKey(
        "Store_Account_requests",
        on_delete=models.CASCADE,
        db_column="request_id",
        verbose_name="申請ID",
    )
    request_status = models.ForeignKey(
        "Application_Statuses",
        on_delete=models.PROTECT,
        db_column="request_status",
        verbose_name="申請ステータス",
    )
    comment = models.TextField(
        verbose_name="コメント",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新日時",
    )
    class Meta:
        db_table = "store_account_request_logs"
        verbose_name = "店舗アカウント申請ログ"
        verbose_name_plural = "店舗アカウント申請ログ"
    def __str__(self):
        return f"Log for Request ID {self.request_id.id} at {self.updated_at}"
#----------------
#フォロー
#----------------
class Follows(models.Model):
    """
    フォロー元ID follower_id								
    フォロー先ID followee_id								
    ブロック済み is_blocked								
    ミュート済み is_muted								
    フォロー日時 followed_at								

    """
    follower_id = models.ForeignKey(
        "Customer_Account",
        on_delete=models.DO_NOTHING,
        related_name="follower",
        db_column="follower_id",
        verbose_name="フォロー元ID",
    )
    followee_id = models.ForeignKey(
        "Customer_Account",
        on_delete=models.DO_NOTHING,
        related_name="followee",
        db_column="followee_id",
        verbose_name="フォロー先ID",
    )
    is_blocked = models.BooleanField(
        verbose_name="ブロック済み",
    )
    is_muted = models.BooleanField(
        verbose_name="ミュート済み",
    )
    followed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="フォロー日時",
    )
    class Meta:
        db_table = "follows"
        verbose_name = "フォロー"
        verbose_name_plural = "フォロー"
        unique_together = (("follower_id", "followee_id"),)
    def __str__(self):
        return f"{self.follower_id.nickname} follows {self.followee_id.nickname}"
#----------------
#口コミ
#----------------
class Reviews(models.Model):
    """
    投稿者ID reviewer_id								
    店舗ID store_id								
    点数 score								
    レビュー review_text								
    口コミ写真 review_photo_id								
    いいね数 like_count								
    投稿日時 posted_at								
    """
    reviewer_id = models.ForeignKey(
        "Customer_Account",
        on_delete=models.PROTECT,
        db_column="reviewer_id",
        verbose_name="投稿者ID",
    )
    store_id = models.ForeignKey(
        "Stores",
        on_delete=models.PROTECT,
        db_column="store_id",
        verbose_name="店舗ID",
    )
    score = models.IntegerField(
        verbose_name="点数",
    )
    review_text = models.TextField(
        verbose_name="レビュー",
    )
    review_photo_id = models.ForeignKey(
        "Review_Photos",
        on_delete=models.PROTECT,
        db_column="review_photo_id",
        verbose_name="口コミ写真",
    )
    like_count = models.IntegerField(
        verbose_name="いいね数",
    )
    posted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="投稿日時",
    )
    class Meta:
        db_table = "reviews"
        verbose_name = "口コミ"
        verbose_name_plural = "口コミ"
    def __str__(self):
        return f"Review by {self.reviewer_id.nickname} for {self.store_id.store_name}"
#----------------
#通報された口コミ
#----------------
class Review_Reports(models.Model):
    """
    口コミID review_id								
    通報者ID reporter_id								
    通報内容 report_text								
    通報ステータス report_status								
    通報日時 reported_at								
    """
    review_id = models.ForeignKey(
        "Reviews",
        on_delete=models.CASCADE,
        db_column="review_id",
        verbose_name="口コミID",
    )
    reporter_id = models.ForeignKey(
        "Account",
        on_delete=models.CASCADE,
        db_column="reporter_id",
        verbose_name="通報者ID",
    )
    report_text = models.TextField(
        verbose_name="通報内容",
    )
    report_status = models.BooleanField(
        verbose_name="通報ステータス",
    )
    reported_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="通報日時",
    )
    class Meta:
        db_table = "review_reports"
        verbose_name = "通報された口コミ"
        verbose_name_plural = "通報された口コミ"
    def __str__(self):
        return f"Report by {self.reporter_id.nickname} on Review ID {self.review_id.id}"
#----------------
#予約者情報
#----------------
class Reservators(models.Model):
    """
    顧客アカウントID customer_account_id NULL OK							
    氏名 full_name								
    氏名かな full_name_kana								
    メールアドレス email								
    電話番号 phone_number								
    """
    customer_account_id = models.ForeignKey(
        "Customer_Account",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_column="customer_account_id",
        verbose_name="顧客アカウントID",
    )
    full_name = models.CharField(
        max_length=100,
        verbose_name="氏名",
    )
    full_name_kana = models.CharField(
        max_length=100,
        verbose_name="氏名かな",
    )
    email = models.EmailField(
        max_length=255,
        verbose_name="メールアドレス",
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name="電話番号",
    )
    class Meta:
        db_table = "reservators"
        verbose_name = "予約者情報"
        verbose_name_plural = "予約者情報"
    def __str__(self):
        return f"{self.full_name} ({self.email})"
#----------------
#予約
#----------------
class Reservations(models.Model):
    """
    予約者ID booking_user_id								
    店舗ID store_id								
    来店日 visit_date								
    来店時刻 visit_time								
    来店人数 visit_count								
    コース course								
    予約ステータス booking_status_id								
    キャンセル理由 cancel_reason								
    作成日時 created_at																
    """
    booking_user_id = models.ForeignKey(
        "Reservators",
        on_delete=models.CASCADE,
        db_column="booking_user_id",
        verbose_name="予約者ID",
    )
    store_id = models.ForeignKey(
        "Stores",
        on_delete=models.CASCADE,
        db_column="store_id",
        verbose_name="店舗ID",
    )
    visit_date = models.DateField(
        verbose_name="来店日",
    )
    visit_time = models.TimeField(
        verbose_name="来店時刻",
    )
    visit_count = models.IntegerField(
        verbose_name="来店人数",
    )
    course = models.CharField(
        max_length=255,
        verbose_name="コース",
    )
    booking_status_id = models.ForeignKey(
        "Reservation_Statuses",
        on_delete=models.PROTECT,
        db_column="booking_status_id",
        verbose_name="予約ステータス",
    )
    cancel_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="キャンセル理由",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="作成日時",
    )
    class Meta:
        db_table = "reservations"
        verbose_name = "予約"
        verbose_name_plural = "予約"
    def __str__(self):
        return f"Reservation by {self.booking_user_id.full_name} at {self.store_id.store_name} on {self.visit_date}"
#----------------
#店舗ネット予約情報
#----------------
class Store_Online_Reservations(models.Model):
    """
    店舗ID store_id PK.FK->stores					
    予約受付状況 booking_status								
    予約可能席数 available_seats								
    日付 date																
    """
    store_id = models.ForeignKey(
        "Stores",
        primary_key=True,
        on_delete=models.CASCADE,
        db_column="store_id",
        verbose_name="店舗ID",
    )
    booking_status = models.BooleanField(
        verbose_name="予約受付状況",
    )
    available_seats = models.IntegerField(
        verbose_name="予約可能席数",
    )
    date = models.DateField(
        verbose_name="日付",
    )
    class Meta:
        db_table = "store_online_reservations"
        verbose_name = "店舗ネット予約情報"
        verbose_name_plural = "店舗ネット予約情報"
    def __str__(self):
        return f"Online Reservation Info for {self.store_id.store_name} on {self.date}"
#----------------
#エリア
#----------------
class Area(models.Model):
    """
    エリア名 area_name								
    """
    area_name = models.CharField(
        max_length=100,
        verbose_name="エリア名",
    )
    class Meta:
        db_table = "area"
        verbose_name = "エリア"
        verbose_name_plural = "エリア"
    def __str__(self):
        return f"{self.area_name}"
#----------------
#利用シーン
#----------------
class Scene(models.Model):
    """
    シーン名 scene_name								
    """
    scene_name = models.CharField(
        max_length=100,
        verbose_name="シーン名",
    )
    class Meta:
        db_table = "scene"
        verbose_name = "利用シーン"
        verbose_name_plural = "利用シーン"
    def __str__(self):
        return f"{self.scene_name}"
#----------------
#パスワードリセットログ
#----------------
class Password_Reset_Log(models.Model):
    """
    リセットトークン reset_token PK					
    アカウントID account_id								
    有効期限 expires_at								
    使用済みフラグ used_flag								
    リセット要求日時 requested_at					
    """
    reset_token = models.CharField(
        primary_key=True,
        max_length=255,
        verbose_name="リセットトークン",
    )
    account_id = models.ForeignKey(
        "Account",
        on_delete=models.CASCADE,
        db_column="account_id",
        verbose_name="アカウントID",
    )
    expires_at = models.DateTimeField(
        verbose_name="有効期限",
    )
    used_flag = models.BooleanField(
        verbose_name="使用済みフラグ",
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="リセット要求日時",
    )
    class Meta:
        db_table = "password_reset_log"
        verbose_name = "パスワードリセットログ"
        verbose_name_plural = "パスワードリセットログ"
    def __str__(self):
        return f"Password Reset for {self.account_id.username} requested at {self.requested_at}"
#----------------
#店舗画像
#----------------
class Store_Images(models.Model):
    """
    店舗ID store_id								
    画像パス image_path								
    画像ステータス image_status_id								
    """
    store_id = models.ForeignKey(
        "Stores",
        on_delete=models.CASCADE,
        db_column="store_id",
        verbose_name="店舗ID",
    )
    image_path = models.CharField(
        max_length=255,
        verbose_name="画像パス",
    )
    image_status_id = models.ForeignKey(
        "Image_Statuses",
        on_delete=models.PROTECT,
        db_column="image_status_id",
        verbose_name="画像ステータス",
    )
    class Meta:
        db_table = "store_images"
        verbose_name = "店舗画像"
        verbose_name_plural = "店舗画像"
    def __str__(self):
        return f"Image for {self.store_id.store_name} - Status ID {self.image_status_id.id}"
#----------------
#メニュー
#----------------
class Store_Menus(models.Model):
    """
    店舗ID store_id								
    メニュー名 menu_name						
    価格 price								
    メニュー画像パス image_path				
    """
    store_id = models.ForeignKey(
        "Stores",
        on_delete=models.CASCADE,
        db_column="store_id",
        verbose_name="店舗ID",
    )
    menu_name = models.CharField(
        max_length=100,
        verbose_name="メニュー名",
    )
    price = models.IntegerField(
        verbose_name="価格",
    )
    image_path = models.CharField(
        max_length=255,
        verbose_name="メニュー画像パス",
    )
    class Meta:
        db_table = "store_menus"
        verbose_name = "メニュー"
        verbose_name_plural = "メニュー"
    def __str__(self):
        return f"{self.menu_name} at {self.store_id.store_name}"
#----------------
#口コミ写真
#----------------
class Review_Photo(models.Model):
    """
    口コミID review_id								
    画像パス image_path								
    """
    review_id = models.ForeignKey(
        "Reviews",
        on_delete=models.CASCADE,
        db_column="review_id",
        verbose_name="口コミID",
    )
    image_path = models.CharField(
        max_length=255,
        verbose_name="画像パス",
    )
    class Meta:
        db_table = "review_photos"
        verbose_name = "口コミ写真"
        verbose_name_plural = "口コミ写真"
    def __str__(self):
        return f"Review Photo at {self.image_path}"
#----------------
#年代マスタ
#----------------
class Age_Groups(models.Model):
    """
    年代 age_range								
    """
    age_range = models.CharField(
        max_length=100,
        verbose_name="年代",
    )
    class Meta:
        db_table = "age_group"
        verbose_name = "年代マスタ"
        verbose_name_plural = "年代マスタ"
    def __str__(self):
        return f"{self.age_range}"
#----------------
#性別マスタ
#----------------
class Genders(models.Model):
    """
    性別 gender
    """
    gender = models.CharField(
        max_length=10,
        verbose_name="性別",
    )
    class Meta:
        db_table = "gender"
        verbose_name = "性別マスタ"
        verbose_name_plural = "性別マスタ"
    def __str__(self):
        return f"{self.gender}"
#----------------
#申請ステータスマスタ
#----------------
class Application_Statuses(models.Model):
    """
    ステータス status								
    """
    status = models.CharField(
        max_length=50,
        verbose_name="ステータス",
    )
    class Meta:
        db_table = "application_statuses"
        verbose_name = "申請ステータスマスタ"
        verbose_name_plural = "申請ステータスマスタ"
    def __str__(self):
        return f"{self.status}"
#----------------
#画像ステータスマスタ
#----------------
class Image_Statuses(models.Model):
    """
    画像ステータス status								
    """
    status = models.CharField(
        max_length=10,
        verbose_name="ステータス",
    )
    class Meta:
        db_table = "image_statuses"
        verbose_name = "画像ステータスマスタ"
        verbose_name_plural = "画像ステータスマスタ"
    def __str__(self):
        return f"{self.status}"
#----------------
#仮申請メールログ
#----------------
class Temp_Request_Mail_Log(models.Model):
    """
    仮申請メールトークン temp_request_token PK						
    申請者ID requester_id								
    有効期限 expires_at								
    使用済みフラグ used_flag								
    要求日時 requested_at								
    """
    temp_request_token = models.CharField(
        primary_key=True,
        max_length=255,
        verbose_name="仮申請メールトークン",
    )
    requester_id = models.ForeignKey(
        "Customer_Account",
        on_delete=models.CASCADE,
        db_column="requester_id",
        verbose_name="申請者ID",
    )
    expires_at = models.DateTimeField(
        verbose_name="有効期限",
    )
    used_flag = models.BooleanField(
        verbose_name="使用済みフラグ",
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="要求日時",
    )
    class Meta:
        db_table = "temp_request_mail_log"
        verbose_name = "仮申請メールログ"
        verbose_name_plural = "仮申請メールログ"
    def __str__(self):
        return f"Temp Request Mail for {self.requester_id.nickname} requested at {self.requested_at}"
#----------------
#アカウント種類マスタ
#----------------
class Account_Type(models.Model):
    """
    アカウント種類 account_type								
    """
    account_type = models.CharField(
        max_length=50,
        verbose_name="アカウント種類",
    )
    class Meta:
        db_table = "account_type"
        verbose_name = "アカウント種類マスタ"
        verbose_name_plural = "アカウント種類マスタ"
    def __str__(self):
        return f"{self.account_type}"
