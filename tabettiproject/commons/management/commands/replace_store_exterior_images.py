import os
import random

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from commons.models import StoreImage, ImageStatus


class Command(BaseCommand):
    help = "ImageStatus=外装 の店舗画像だけを、用意した画像プールで一括置換する（DBは触らない）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pool",
            type=str,
            default="media/_pool/store_exterior",
            help="外装画像プールのパス（プロジェクト直下からの相対パス）例: media/_pool/store_exterior",
        )
        parser.add_argument(
            "--rotate",
            action="store_true",
            help="ランダムではなく均等ローテーションで割り当てる",
        )
        parser.add_argument(
            "--status",
            type=str,
            default="外装",
            help="対象にする ImageStatus.status（デフォルト: 外装）",
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
            raise CommandError(f"プールに画像がありません: {pool_dir}")

        status_name = options["status"]

        try:
            target_status = ImageStatus.objects.get(status=status_name)
        except ImageStatus.DoesNotExist:
            raise CommandError(f"ImageStatus に '{status_name}' が存在しません")

        qs = StoreImage.objects.filter(image_status=target_status)

        if not qs.exists():
            self.stdout.write(self.style.WARNING(f"ImageStatus='{status_name}' の StoreImage が 0 件です"))
            return

        count = 0
        idx = 0

        for si in qs.iterator():
            if not si.image_file:
                continue

            dst_path = si.image_file.path

            if options["rotate"]:
                src_path = pool_files[idx % len(pool_files)]
                idx += 1
            else:
                src_path = random.choice(pool_files)

            os.makedirs(os.path.dirname(dst_path), exist_ok=True)

            with open(src_path, "rb") as src, open(dst_path, "wb") as dst:
                dst.write(src.read())

            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: ImageStatus='{status_name}' の画像 {count} 件を置換しました（プール {len(pool_files)} 枚）"
            )
        )
