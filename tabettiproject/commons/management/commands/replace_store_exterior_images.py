import os
import random
import shutil
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from commons.models import Store, StoreImage, ImageStatus


def _list_files(abs_dir: str) -> list[str]:
    if not os.path.isdir(abs_dir):
        return []
    files = []
    for f in os.listdir(abs_dir):
        p = os.path.join(abs_dir, f)
        if os.path.isfile(p):
            files.append(p)
    return sorted(files)


class Command(BaseCommand):
    """
    外装画像（ImageStatus.status == '外装'）だけを対象に、
    - 既存外装は image_file をプール画像で置換
    - 外装が0枚の店舗には最低1枚を新規追加
    - 既存レコードは削除しない
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--pool",
            type=str,
            default="media/_pool/store/exterior",
            help="外装プール画像フォルダ（BASE_DIR からの相対パス）",
        )
        parser.add_argument(
            "--rotate",
            action="store_true",
            help="プール画像を均等ローテで使う（指定なしはランダム）",
        )
        parser.add_argument(
            "--dryrun",
            action="store_true",
            help="差し替え/作成はせず、対象件数だけ表示",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="0=無制限 / 例: 50 のように指定すると修正件数を制限",
        )

    def handle(self, *args, **opt):
        if not settings.MEDIA_ROOT:
            raise CommandError("MEDIA_ROOT が設定されていません")

        pool_dir = os.path.join(settings.BASE_DIR, opt["pool"])
        pool = _list_files(pool_dir)
        if not pool:
            raise CommandError(f"外装プールが空です: {pool_dir}")

        try:
            st_exterior = ImageStatus.objects.get(status="外装")
        except ImageStatus.DoesNotExist:
            raise CommandError("ImageStatus に '外装' がありません")

        # 書き込み先（StoreImage.image_file の upload_to は store/images/）
        dst_dir = os.path.join(settings.MEDIA_ROOT, "store", "images")
        os.makedirs(dst_dir, exist_ok=True)

        rotate = bool(opt["rotate"])
        limit = int(opt["limit"] or 0)

        # 対象件数の見積もり
        total_stores = Store.objects.count()
        ext_qs = StoreImage.objects.filter(image_status=st_exterior).only("id", "store_id", "image_file")
        ext_existing_count = ext_qs.count()

        stores_with_ext = set(ext_qs.values_list("store_id", flat=True).distinct())
        stores_without_ext_count = Store.objects.exclude(id__in=stores_with_ext).count()

        self.stdout.write(f"総店舗数: {total_stores}")
        self.stdout.write(f"既存 外装レコード数: {ext_existing_count}")
        self.stdout.write(f"外装0枚の店舗数（最低1枚追加対象）: {stores_without_ext_count}")
        if opt["dryrun"]:
            self.stdout.write("dryrun のため変更しません")
            return

        # プール選択
        pool_index = 0

        def pick() -> str:
            nonlocal pool_index
            if rotate:
                src = pool[pool_index % len(pool)]
                pool_index += 1
                return src
            return random.choice(pool)

        replaced = 0
        created = 0

        with transaction.atomic():
            # 1) 既存外装を置換（レコードはそのまま、image_file だけ差し替え）
            for si in ext_qs.order_by("id").iterator():
                if limit and (replaced + created) >= limit:
                    break

                src = pick()
                ext = os.path.splitext(src)[1].lower() or ".png"
                new_filename = f"exterior_{si.store_id}_{si.id}_{uuid4().hex}{ext}"

                abs_dst = os.path.join(dst_dir, new_filename)
                shutil.copy2(src, abs_dst)

                si.image_file.name = f"store/images/{new_filename}"
                si.save(update_fields=["image_file"])
                replaced += 1

            # 2) 外装0枚の店舗に最低1枚追加
            #    limit がある場合、置換で上限に達してたら追加しない
            if not limit or (replaced + created) < limit:
                store_ids_without = Store.objects.exclude(id__in=stores_with_ext).values_list("id", flat=True)
                for store_id in store_ids_without.iterator():
                    if limit and (replaced + created) >= limit:
                        break

                    src = pick()
                    ext = os.path.splitext(src)[1].lower() or ".png"
                    new_filename = f"exterior_{store_id}_new_{uuid4().hex}{ext}"

                    abs_dst = os.path.join(dst_dir, new_filename)
                    shutil.copy2(src, abs_dst)

                    si = StoreImage.objects.create(
                        store_id=store_id,
                        image_status=st_exterior,
                        image_path="",
                    )
                    si.image_file.name = f"store/images/{new_filename}"
                    si.save(update_fields=["image_file"])
                    created += 1

        self.stdout.write(self.style.SUCCESS(
            f"完了: 置換={replaced} / 追加(外装0店舗への最低1枚)={created}"
        ))
