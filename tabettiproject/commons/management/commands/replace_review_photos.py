import os
import random

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from commons.models import ReviewPhoto


class Command(BaseCommand):
    help = "ReviewPhoto の画像を、用意した画像プールで一括置換する（DBは触らない）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pool",
            type=str,
            default="media/_pool/review",
            help="口コミ画像プールのパス（プロジェクト直下からの相対パス）例: media/_pool/review",
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
            raise CommandError(f"プールに画像がありません: {pool_dir}")

        qs = ReviewPhoto.objects.all()
        if not qs.exists():
            self.stdout.write(self.style.WARNING("ReviewPhoto が 0 件です"))
            return

        count = 0
        idx = 0

        for rp in qs.iterator():
            if not rp.image_path:
                continue

            # ImageField の実ファイル
            dst_path = rp.image_path.path

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
                f"完了: 口コミ写真 {count} 件を置換しました（プール {len(pool_files)} 枚）"
            )
        )
