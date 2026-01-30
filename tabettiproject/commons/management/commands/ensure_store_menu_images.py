import os
import random

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from commons.models import Store, StoreMenu


AUTO_MENU_STORE_ID_MIN = 209
AUTO_MENU_STORE_ID_MAX = 390


class Command(BaseCommand):
    help = "ID209-390の店舗に、StoreMenuが0件なら自動生成し、画像プールから image_file を割り当てる"

    def add_arguments(self, parser):
        parser.add_argument("--min-id", type=int, default=AUTO_MENU_STORE_ID_MIN)
        parser.add_argument("--max-id", type=int, default=AUTO_MENU_STORE_ID_MAX)
        parser.add_argument(
            "--pool",
            type=str,
            default="media/_pool/store/food",
            help='画像プール（BASE_DIRからの相対パス）例: "media/_pool/store/food"',
        )
        parser.add_argument("--per-store", type=int, default=6, help="1店舗あたり作るメニュー数（メニュー0件の店舗のみ）")
        parser.add_argument("--rotate", action="store_true", help="ランダムではなく均等ローテーションで割り当てる")
        parser.add_argument("--dry-run", action="store_true", help="DB保存せず件数だけ表示")

    def handle(self, *args, **opts):
        if not settings.MEDIA_ROOT:
            raise CommandError("MEDIA_ROOT が設定されていません")

        min_id = int(opts["min_id"])
        max_id = int(opts["max_id"])
        per_store = int(opts["per_store"])
        pool_rel = (opts["pool"] or "").strip().replace("\\", "/")
        rotate = bool(opts["rotate"])
        dry = bool(opts["dry_run"])

        pool_dir = os.path.join(settings.BASE_DIR, pool_rel)
        if not os.path.isdir(pool_dir):
            raise CommandError(f"プールフォルダが存在しません: {pool_dir}")

        pool_files = [
            os.path.join(pool_dir, f)
            for f in os.listdir(pool_dir)
            if os.path.isfile(os.path.join(pool_dir, f))
        ]
        if not pool_files:
            raise CommandError(f"プールに画像がありません: {pool_dir}")

        base_names = [
            "おすすめ盛り合わせ",
            "季節の前菜",
            "お刺身盛り",
            "焼き物",
            "揚げ物",
            "〆の一品",
            "デザート",
            "ドリンク",
        ]

        stores = Store.objects.filter(id__gte=min_id, id__lte=max_id).order_by("id")

        total_created = 0
        total_updated = 0
        pool_idx = 0

        for s in stores.iterator():
            existing_count = StoreMenu.objects.filter(store=s).count()

            created = 0
            updated = 0

            if existing_count == 0:
                # メニューを作る
                if dry:
                    created = per_store
                else:
                    new_objs = []
                    for i in range(per_store):
                        name = base_names[i % len(base_names)]
                        price = 700 + (i * 150)
                        new_objs.append(
                            StoreMenu(
                                store=s,
                                menu_name=name,
                                price=price,
                                image_path="----",
                            )
                        )
                    StoreMenu.objects.bulk_create(new_objs)
                    created = len(new_objs)

                # 作った（or 作る予定の）メニューに画像割り当て
                if not dry and created > 0:
                    qs = StoreMenu.objects.filter(store=s).order_by("id")[:per_store]
                    for i, menu in enumerate(qs):
                        src = pool_files[(pool_idx + i) % len(pool_files)] if rotate else random.choice(pool_files)
                        with open(src, "rb") as f:
                            menu.image_file.save(os.path.basename(src), File(f), save=True)
                        updated += 1
                    pool_idx += per_store

            self.stdout.write(f"[store:{s.id}] menus={existing_count} created={created} updated={updated}")

            total_created += created
            total_updated += updated

        self.stdout.write(
            self.style.SUCCESS(
                f"done. stores={stores.count()}, total_created={total_created}, total_updated={total_updated}, pool={len(pool_files)}"
            )
        )
