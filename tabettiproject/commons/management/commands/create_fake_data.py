from django.core.management.base import BaseCommand
from faker import Faker
from commons.models import (
    AccountType, AgeGroup, Gender, Scene, Area, ReservationStatus,
    CustomerAccount, StoreAccount, Store,
    Review, Follow,
    Reservator, Reservation,
    StoreImage, StoreMenu
)
import random
from datetime import date, time

class Command(BaseCommand):
    help = "マスタ以外の疑似データを作成する"

    def handle(self, *args, **options):
        fake = Faker('ja_JP')

        # -----------------------------
        # マスタ取得（既存前提）
        # -----------------------------
        account_type_customer = AccountType.objects.get(account_type="顧客")
        account_type_store = AccountType.objects.get(account_type="店舗")

        age_groups = list(AgeGroup.objects.all())
        genders = list(Gender.objects.all())
        scenes = list(Scene.objects.all())
        areas = list(Area.objects.all())
        reservation_status = ReservationStatus.objects.first()

        # -----------------------------
        # 顧客アカウント作成
        # -----------------------------
        customers = []
        for _ in range(10):
            user = CustomerAccount.objects.create_user(
                username=fake.user_name(),
                password="password123",
                email=fake.email(),
                account_type=account_type_customer,
                nickname=fake.name(),
                sub_email=fake.email(),
                phone_number=fake.phone_number(),
                age_group=random.choice(age_groups),
                address=fake.address(),
                title="一般ユーザー",
                location=fake.city(),
                birth_date=fake.date_of_birth(minimum_age=18, maximum_age=70),
                gender=random.choice(genders),
            )
            customers.append(user)

        self.stdout.write(self.style.SUCCESS("顧客アカウント作成完了"))

        # -----------------------------
        # 店舗作成
        # -----------------------------
        stores = []
        for _ in range(5):
            store = Store.objects.create(
                store_name=fake.company(),
                branch_name=fake.city(),
                email=fake.company_email(),
                phone_number=fake.phone_number(),
                address=fake.address(),
                map_location="GoogleMap",
                area=random.choice(areas),
                business_hours="11:00〜22:00",
                seats=random.randint(10, 80),
                budget=random.randint(1000, 5000),
                scene=random.choice(scenes),
                creator=random.choice(customers)
            )
            stores.append(store)

        self.stdout.write(self.style.SUCCESS("店舗作成完了"))

        # -----------------------------
        # 店舗アカウント作成
        # -----------------------------
        for store in stores:
            StoreAccount.objects.create_user(
                username=f"store_{store.id}",
                password="password123",
                email=store.email,
                account_type=account_type_store,
                store=store,
                admin_email=store.email,
                permission_flag=True
            )

        self.stdout.write(self.style.SUCCESS("店舗アカウント作成完了"))

        # -----------------------------
        # レビュー作成
        # -----------------------------
        reviews = []
        for _ in range(20):
            review = Review.objects.create(
                reviewer=random.choice(customers),
                store=random.choice(stores),
                score=random.randint(1, 5),
                review_text=fake.text(max_nb_chars=100),
                like_count=random.randint(0, 50)
            )
            reviews.append(review)

        self.stdout.write(self.style.SUCCESS("レビュー作成完了"))

        # -----------------------------
        # フォロー作成
        # -----------------------------
        for _ in range(20):
            follower, followee = random.sample(customers, 2)
            Follow.objects.get_or_create(
                follower=follower,
                followee=followee
            )

        self.stdout.write(self.style.SUCCESS("フォロー作成完了"))

        # -----------------------------
        # 予約者・予約作成
        # -----------------------------
        for _ in range(10):
            reservator = Reservator.objects.create(
                customer_account=random.choice(customers),
                full_name=fake.name(),
                full_name_kana="テスト タロウ",
                email=fake.email(),
                phone_number=fake.phone_number()
            )

            Reservation.objects.create(
                booking_user=reservator,
                store=random.choice(stores),
                visit_date=fake.date_between(start_date='today', end_date='+30d'),
                visit_time=time(hour=random.randint(11, 20)),
                visit_count=random.randint(1, 6),
                course="通常コース",
                booking_status=reservation_status
            )

        self.stdout.write(self.style.SUCCESS("予約作成完了"))

        self.stdout.write(self.style.SUCCESS("=== 疑似データ作成 完了 ==="))
