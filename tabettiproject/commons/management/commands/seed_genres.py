from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from commons.models import Genre


GENRE_NAMES = [
    "日本料理・懐石",
    "寿司・海鮮",
    "うなぎ・肉料理(和)",
    "天ぷら・揚げ物",
    "焼き鳥・鳥料理",
    "そば・うどん・麺",
    "丼・お好み焼き・おでん",
    "イタリアン・フレンチ",
    "洋食・ステーキ",
    "各国料理(欧米)",
    "中華料理",
    "韓国料理",
    "アジア・エスニック",
    "カレー",
    "焼肉・ホルモン",
    "鍋料理",
    "ラーメン・麺専門店",
    "居酒屋・ダイニングバー",
    "バー・パブ",
    "ビアガーデン・ホール",
    "カフェ・喫茶店",
    "パン・サンドイッチ",
    "スイーツ・和菓子",
    "レストラン・食堂",
    "その他施設",
]


class Command(BaseCommand):
    help = "customer_genre_list.html に出てくるジャンル名を Genre マスタへ一括登録します（既存はスキップ）"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="保存せず表示のみ")

    @transaction.atomic
    def handle(self, *args, **opts):
        dry_run: bool = opts["dry_run"]

        created = 0
        skipped = 0

        for name in GENRE_NAMES:
            obj, is_created = Genre.objects.get_or_create(name=name)
            if is_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"CREATE: {name}"))
            else:
                skipped += 1
                self.stdout.write(f"SKIP: {name}")

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("DRY-RUN: ロールバックしました"))
            return

        self.stdout.write(self.style.SUCCESS(f"完了: create={created} / skip={skipped}"))
