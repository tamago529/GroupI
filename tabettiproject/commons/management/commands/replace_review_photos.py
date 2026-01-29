import os
import random

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from commons.models import ReviewPhoto


class Command(BaseCommand):
    help = "ReviewPhoto(image_path) の実ファイルを、DBが指す review/photos 配下に一括置換（DBは触らない）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pool",
            type=str,
            default="media/_pool/review",
            help="置換用画像プール（プロジェクト直下からの相対パス）例: media/_pool/review",
        )
        parser.add_argument(
            "--rotate",
            action="store_true",
            help="ランダムではなく均等ローテーションで割り当てる",
        )

    def handle(self, *args, **options):
        if not settings.MEDIA_ROOT:
            raise CommandError("MEDIA_ROOT が設定されていません")

        # プール読み込み
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

        # ★DBが指している場所に合わせる（ここがポイント）
        # 例：review/photos/review_4859_1.png
        dst_root = os.path.join(settings.MEDIA_ROOT, "review", "photos")
        os.makedirs(dst_root, exist_ok=True)

        count = 0
        idx = 0
        skipped = 0

        for rp in qs.iterator():
            if not rp.image_path:
                skipped += 1
                continue

            # DBの name を基準に「ファイル名」を維持して上書き
            filename = os.path.basename(rp.image_path.name)  # review_4859_1.png
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
                f"完了: review/photos に {count} 件 置換しました（skip={skipped}, pool={len(pool_files)}）"
            )
        )
