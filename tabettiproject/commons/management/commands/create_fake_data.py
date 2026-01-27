from __future__ import annotations

import os
import random
from datetime import time

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from faker import Faker

from commons.models import (
    AccountType, AgeGroup, Gender, Scene, Area,
    ReservationStatus, ImageStatus,
    CustomerAccount, StoreAccount, Store,
    Review, ReviewPhoto, Follow,
    Reservator, Reservation,
    StoreImage, StoreMenu,
)

# ============================
# ダミーPNG（1x1 / Pillow不要）
# ============================
DUMMY_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDATx\x9cc``\x00\x00"
    b"\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)

def require_non_empty(items, name: str):
    if not items:
        raise CommandError(f"{name} が0件です。先に管理画面でマスタを登録してください。")

def ensure_media_root() -> str:
    if not settings.MEDIA_ROOT:
        raise CommandError("settings.MEDIA_ROOT が設定されていません。")
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    return settings.MEDIA_ROOT

def write_dummy_png(rel_path: str) -> str:
    """MEDIA_ROOT からの相対パスで PNG を生成"""
    root = ensure_media_root()
    abs_path = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    if not os.path.exists(abs_path):
        with open(abs_path, "wb") as f:
            f.write(DUMMY_PNG_BYTES)
    return abs_path


class Command(BaseCommand):
    help = "疑似データ完全生成（レビュー写真0枚混在・画像ファイル生成対応）"

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=1000)
        parser.add_argument("--stores", type=int, default=200)
        parser.add_argument("--store_accounts_percent", type=int, default=70)

        parser.add_argument("--reviews", type=int, default=5000)
        parser.add_argument("--follows", type=int, default=5000)
        parser.add_argument("--reservators", type=int, default=2000)
        parser.add_argument("--reservations", type=int, default=3000)

        parser.add_argument("--store_images_per_store", type=int, default=5)
        parser.add_argument("--menus_per_store", type=int, default=10)

        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opt):
        fake = Faker("ja_JP")
        random.seed(opt["seed"])
        Faker.seed(opt["seed"])

        # ----------------------------
        # マスタ取得
        # ----------------------------
        age_groups = list(AgeGroup.objects.all())
        genders = list(Gender.objects.all())
        areas = list(Area.objects.all())
        statuses = list(ReservationStatus.objects.all())
        image_statuses = list(ImageStatus.objects.all())

        require_non_empty(age_groups, "AgeGroup")
        require_non_empty(genders, "Gender")
        require_non_empty(areas, "Area")
        require_non_empty(statuses, "ReservationStatus")
        require_non_empty(image_statuses, "ImageStatus")

        scenes = list(Scene.objects.all())
        if not scenes:
            Scene.objects.bulk_create([
                Scene(scene_name=s) for s in
                ["デート", "家族", "友人", "一人", "接待", "飲み会", "記念日", "ランチ", "ディナー"]
            ])
            scenes = list(Scene.objects.all())

        account_type_customer = AccountType.objects.get(account_type="顧客")
        account_type_store = AccountType.objects.get(account_type="店舗")

        # ----------------------------
        # reset（必要なときだけ）
        # ----------------------------
        if opt["reset"]:
            Reservation.objects.all().delete()
            Reservator.objects.all().delete()
            Follow.objects.all().delete()
            ReviewPhoto.objects.all().delete()
            Review.objects.all().delete()
            StoreMenu.objects.all().delete()
            StoreImage.objects.all().delete()
            StoreAccount.objects.all().delete()
            Store.objects.all().delete()
            CustomerAccount.objects.all().delete()

        # ----------------------------
        # 顧客作成
        # ----------------------------
        customers = []
        start = (CustomerAccount.objects.aggregate(m=Max("id"))["m"] or 0) + 1

        for i in range(opt["customers"]):
            customers.append(
                CustomerAccount.objects.create_user(
                    username=f"cust_{start+i}",
                    email=fake.email(),
                    password="password123",
                    account_type=account_type_customer,
                    nickname=fake.name(),
                    sub_email=fake.email(),
                    phone_number=fake.phone_number(),
                    age_group=random.choice(age_groups),
                    address=fake.address(),
                    title="一般ユーザー",
                    location=fake.city(),
                    # ★ 修正済み：正しい呼び方
                    birth_date=fake.date_of_birth(minimum_age=18, maximum_age=70),
                    gender=random.choice(genders),
                )
            )

        # ----------------------------
        # 店舗作成
        # ----------------------------
        store_objs = []
        for _ in range(opt["stores"]):
            store_objs.append(
                Store(
                    store_name=fake.company(),
                    branch_name=fake.city(),
                    email=fake.company_email(),
                    phone_number=fake.phone_number(),
                    address=fake.address(),
                    map_location="GoogleMap",
                    area=random.choice(areas),
                    business_hours="11:00〜22:00",
                    open_time_1=time(11),
                    close_time_1=time(15),
                    open_time_2=time(17),
                    close_time_2=time(22),
                    seats=random.randint(10, 120),
                    budget=random.randint(800, 8000),
                    genre=random.choice(["和食", "洋食", "中華", "焼肉", "カフェ"]),
                    scene=random.choice(scenes),
                    creator=random.choice(customers),
                )
            )

        Store.objects.bulk_create(store_objs, batch_size=500)
        stores = list(Store.objects.order_by("-id")[: opt["stores"]])

        # ----------------------------
        # 店舗アカウント（混在）
        # ----------------------------
        k = int(len(stores) * opt["store_accounts_percent"] / 100)
        for s in random.sample(stores, k):
            StoreAccount.objects.create_user(
                username=f"store_{s.id}",
                email=s.email,
                password="password123",
                account_type=account_type_store,
                store=s,
                admin_email=s.email,
                permission_flag=True,
            )

        # ----------------------------
        # 店舗画像
        # ----------------------------
        images = []
        for s in stores:
            for i in range(opt["store_images_per_store"]):
                rel = f"store/images/store_{s.id}_{i}.png"
                abs_path = write_dummy_png(rel)
                img = StoreImage(store=s, image_path=rel, image_status=random.choice(image_statuses))
                with open(abs_path, "rb") as f:
                    img.image_file.save(os.path.basename(rel), File(f), save=False)
                images.append(img)
        StoreImage.objects.bulk_create(images, batch_size=1000)

        # ----------------------------
        # メニュー
        # ----------------------------
        menus = []
        for s in stores:
            for i in range(opt["menus_per_store"]):
                rel = f"store/menus/menu_{s.id}_{i}.png"
                abs_path = write_dummy_png(rel)
                m = StoreMenu(store=s, menu_name=f"メニュー{i+1}", price=random.randint(300, 3000), image_path=rel)
                with open(abs_path, "rb") as f:
                    m.image_file.save(os.path.basename(rel), File(f), save=False)
                menus.append(m)
        StoreMenu.objects.bulk_create(menus, batch_size=1000)

        # ----------------------------
        # レビュー
        # ----------------------------
        reviews = []
        for _ in range(opt["reviews"]):
            reviews.append(
                Review(
                    reviewer=random.choice(customers),
                    store=random.choice(stores),
                    score=random.randint(1, 5),
                    review_text=fake.text(max_nb_chars=120),
                    like_count=random.randint(0, 200),
                )
            )
        Review.objects.bulk_create(reviews, batch_size=1000)
        created_reviews = list(Review.objects.order_by("-id")[: opt["reviews"]])

        # ----------------------------
        # 口コミ写真（20%は0枚 / 他は1〜3枚）
        # ----------------------------
        photos = []
        for r in created_reviews:
            if random.random() < 0.20:
                continue
            for i in range(random.randint(1, 3)):
                rel = f"review_photos/review_{r.id}_{i}.png"
                abs_path = write_dummy_png(rel)
                rp = ReviewPhoto(review=r)
                with open(abs_path, "rb") as f:
                    rp.image_path.save(f"review_{r.id}_{i}.png", File(f), save=False)
                photos.append(rp)
        ReviewPhoto.objects.bulk_create(photos, batch_size=1000)

        self.stdout.write(self.style.SUCCESS("=== 疑似データ生成 完了 ==="))
