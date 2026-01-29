import os
import random

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from commons.models import StoreImage, ImageStatus


class Command(BaseCommand):
    help = "ImageStatus=内装 の店舗画像だけを、画像プールで一括置換する（DBは触らない）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pool",
            type=str,
            default="media/_pool/store/interior",
            help="内装画像プール（プロジェクト直下からの相対パス）",
        )
        parser.add_argument(
            "--rotate",
            action="store_true",
            help="ランダムではなく均等ローテーションで割り当てる",
        )

    def handle(self, *args, **options):
        if not settings.MEDIA_ROOT:
            raise CommandError("MEDIA_ROOT が設定されていません")

        pool_dir = os.path.join(settings.BASE_DIR, options["pool"])
        if not os.path.isdir(pool_dir):
            raise CommandError(f"プールフォルダが存在しません: {pool_dir}")

        pool_files = [
            os.path.join(pool_dir, f)
            for f in os.listdir(pool_dir)
            if os.path.isfile(os.path.join(pool_dir, f))
        ]
        if not pool_files:
            raise CommandError("画像プールが空です")

        try:
            interior_status = ImageStatus.objects.get(status="内装")
        except ImageStatus.DoesNotExist:
            raise CommandError("ImageStatus に '内装' が存在しません")

        qs = StoreImage.objects.filter(image_status=interior_status)
        if not qs.exists():
            self.stdout.write(self.style.WARNING("内装画像が 0 件です"))
            return

        dst_root = os.path.join(settings.MEDIA_ROOT, "store", "images")
        os.makedirs(dst_root, exist_ok=True)

        count = 0
        idx = 0

        for si in qs.iterator():
            if not si.image_file:
                continue

            filename = os.path.basename(si.image_file.name)
            dst_path = os.path.join(dst_root, filename)

            if options["rotate"]:
                src_path = pool_files[idx % len(pool_files)]
                idx += 1
            else:
                src_path = random.choice(pool_files)

            with open(src_path, "rb") as src, open(dst_path, "wb") as dst:
                dst.write(src.read())

            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: 内装画像 {count} 件を置換しました（pool={len(pool_files)}）"
            )
        )
