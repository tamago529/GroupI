import os
import random
import shutil
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from commons.models import Store, StoreImage, ImageStatus


class Command(BaseCommand):
    """
    全店舗を対象に、
    内装1枚・料理(料理1-5のいずれか)1枚・メニュー表(メニュー表1-5のいずれか)1枚
    を「不足分だけ追加」する（既存は削除しない）。
    ※ 外装は対象外
    """

    def add_arguments(self, parser):
        parser.add_argument("--interior_pool", type=str, default="media/_pool/store/interior")
        parser.add_argument("--food_pool", type=str, default="media/_pool/store/food")
        parser.add_argument("--menu_table_pool", type=str, default="media/_pool/store/menu_table")
        parser.add_argument("--rotate", action="store_true", help="均等ローテ（指定なしはランダム）")

    def _load_pool(self, rel_path: str):
        pool_dir = os.path.join(settings.BASE_DIR, rel_path)
        if not os.path.isdir(pool_dir):
            raise CommandError(f"プールフォルダが存在しません: {pool_dir}")
        files = [
            os.path.join(pool_dir, f)
            for f in os.listdir(pool_dir)
            if os.path.isfile(os.path.join(pool_dir, f))
        ]
        if not files:
            raise CommandError(f"プール画像が 0 件です: {pool_dir}")
        return files

    def _pick(self, pool, idx, rotate):
        if rotate:
            return pool[idx % len(pool)], idx + 1
        return random.choice(pool), idx

    @transaction.atomic
    def handle(self, *args, **opt):
        if not settings.MEDIA_ROOT:
            raise CommandError("MEDIA_ROOT が設定されていません")

        pools = {
            "interior": self._load_pool(opt["interior_pool"]),
            "food": self._load_pool(opt["food_pool"]),
            "menu": self._load_pool(opt["menu_table_pool"]),
        }

        try:
            st_interior = ImageStatus.objects.get(status="内装")
        except ImageStatus.DoesNotExist:
            raise CommandError("ImageStatus に '内装' がありません")

        food_statuses = list(ImageStatus.objects.filter(status__startswith="料理").order_by("status"))
        if not food_statuses:
            raise CommandError("ImageStatus に '料理*' がありません")

        menu_statuses = list(ImageStatus.objects.filter(status__startswith="メニュー表").order_by("status"))
        if not menu_statuses:
            raise CommandError("ImageStatus に 'メニュー表*' がありません")

        dst_root = os.path.join(settings.MEDIA_ROOT, "store", "images")
        os.makedirs(dst_root, exist_ok=True)

        idx_i = idx_f = idx_m = 0
        created = {"interior": 0, "food": 0, "menu": 0}

        # ★ 全店舗対象にする（ここが修正点）
        for store_id in Store.objects.values_list("id", flat=True).iterator():
            qs = StoreImage.objects.filter(store_id=store_id)

            has_interior = qs.filter(image_status=st_interior).exists()
            has_food = qs.filter(image_status__in=food_statuses).exists()
            has_menu = qs.filter(image_status__in=menu_statuses).exists()

            if not has_interior:
                src, idx_i = self._pick(pools["interior"], idx_i, opt["rotate"])
                filename = f"store_int_{store_id}_{uuid4().hex}.png"
                shutil.copy2(src, os.path.join(dst_root, filename))
                si = StoreImage.objects.create(store_id=store_id, image_status=st_interior, image_path="")
                si.image_file.name = f"store/images/{filename}"
                si.save(update_fields=["image_file"])
                created["interior"] += 1

            if not has_food:
                src, idx_f = self._pick(pools["food"], idx_f, opt["rotate"])
                filename = f"store_food_{store_id}_{uuid4().hex}.png"
                shutil.copy2(src, os.path.join(dst_root, filename))
                si = StoreImage.objects.create(
                    store_id=store_id,
                    image_status=random.choice(food_statuses),
                    image_path=""
                )
                si.image_file.name = f"store/images/{filename}"
                si.save(update_fields=["image_file"])
                created["food"] += 1

            if not has_menu:
                src, idx_m = self._pick(pools["menu"], idx_m, opt["rotate"])
                filename = f"store_menu_{store_id}_{uuid4().hex}.png"
                shutil.copy2(src, os.path.join(dst_root, filename))
                si = StoreImage.objects.create(
                    store_id=store_id,
                    image_status=random.choice(menu_statuses),
                    image_path=""
                )
                si.image_file.name = f"store/images/{filename}"
                si.save(update_fields=["image_file"])
                created["menu"] += 1

        self.stdout.write(self.style.SUCCESS(
            f"完了: 内装追加={created['interior']} / 料理追加={created['food']} / メニュー表追加={created['menu']} "
            "（既存は削除していません）"
        ))
