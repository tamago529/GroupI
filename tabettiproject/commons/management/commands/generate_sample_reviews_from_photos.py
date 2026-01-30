# commons/management/commands/generate_sample_reviews_from_photos.py
from __future__ import annotations

import json
import random
import os
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from commons.models import Review


# -----------------------------
# サンプル文（断定を避ける / 写真だけで味や雰囲気を確定しない）
# ※「サンプル（自動生成）」を必ず明記する
# -----------------------------
PREFIX = "【サンプル（自動生成）】"

LINE1_CHOICES = [
    "写真映えする一皿で、盛り付けがきれいでした。",
    "見た目の印象が良く、手が込んでいそうに感じました。",
    "色合いがよくて、つい写真を撮りたくなる雰囲気でした。",
    "提供された料理の見た目が魅力的でした。",
]

# 味は写真だけでは確定できないので「〜に感じた」「〜そう」等に寄せる
LINE2_CHOICES = [
    "ひと口目から満足できそうな雰囲気で、また別メニューも試したいです。",
    "食感やバランスが良さそうで、全体的に丁寧さを感じました。",
    "香りや温度感まで伝わってきそうで、期待が高まりました。",
    "シンプルだけど飽きにくそうな印象で、リピートしたくなりました。",
]

# 店内の雰囲気も写真だけでは確定しない（料理写真しか無いケースが多い）ので断定しない
LINE3_CHOICES = [
    "お店の空気感も落ち着いていそうで、ゆっくり食事できそうです。",
    "雰囲気も良さそうで、友人と行くのにも向いていそうです。",
    "店内も心地よさそうで、また行きたいと思いました。",
    "スタッフさんの丁寧さも期待できそうで、安心感がありました。",
]


def _build_text(*, score: int, photo_count: int) -> str:
    """
    ✅ 要望対応：
    - review_text 内に「評価」「写真◯枚」などのメタ文面を入れない
    - 3行固定
    ※ score/photo_count は将来拡張用に引数として残す（未使用）
    """
    l1 = random.choice(LINE1_CHOICES)
    l2 = random.choice(LINE2_CHOICES)
    l3 = random.choice(LINE3_CHOICES)
    return "\n".join([f"{PREFIX}{l1}", l2, l3])


class Command(BaseCommand):
    help = "レビュー写真の有無など“事実”に基づき、サンプル（自動生成）口コミ文へ一括置換します（3行固定）。"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="保存せず差分のみ表示")
        parser.add_argument("--limit", type=int, default=0, help="処理件数制限（0=無制限）")
        parser.add_argument(
            "--only-has-photos",
            action="store_true",
            help="写真が1枚以上あるレビューだけ対象にする",
        )
        parser.add_argument(
            "--only-if-empty",
            action="store_true",
            help="review_text が空/ほぼ空のものだけ対象にする",
        )
        parser.add_argument(
            "--include-existing-samples",
            action="store_true",
            help="既にサンプル（自動生成）のものも作り直す（PREFIX始まりも対象）",
        )
        parser.add_argument(
            "--backup",
            type=str,
            default="",
            help="変更前後をJSONで保存するパス（例: backups/sample_reviews.json）",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=0,
            help="乱数シード（再現性が必要なら指定）",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        limit: int = int(options["limit"] or 0)
        only_has_photos: bool = options["only_has_photos"]
        only_if_empty: bool = options["only_if_empty"]
        include_existing_samples: bool = options["include_existing_samples"]
        backup_path: str = (options["backup"] or "").strip()
        seed: int = int(options["seed"] or 0)

        if seed:
            random.seed(seed)

        qs = (
            Review.objects
            .select_related("store", "reviewer")
            .prefetch_related("photos")
            .order_by("id")
        )

        seen = 0
        changed = 0
        to_save: list[Review] = []
        backup_rows: list[dict] = []

        for r in qs.iterator(chunk_size=200):
            seen += 1
            if limit and seen > limit:
                break

            photo_count = r.photos.count() if hasattr(r, "photos") else 0
            if only_has_photos and photo_count <= 0:
                continue

            old = (r.review_text or "").strip()
            if only_if_empty and len(old) >= 10:
                continue

            # 既にサンプルなら二重生成しない（ただし --include-existing-samples なら作り直す）
            if (not include_existing_samples) and old.startswith(PREFIX):
                continue

            new_text = _build_text(score=int(r.score or 0), photo_count=int(photo_count)).strip()
            if not new_text or new_text == old:
                continue

            backup_rows.append({
                "id": r.id,
                "store_id": r.store_id,
                "reviewer_id": r.reviewer_id,
                "score": int(r.score or 0),
                "photo_count": int(photo_count),
                "old": old,
                "new": new_text,
            })

            if dry_run:
                self.stdout.write(self.style.WARNING(f"[DRY] Review id={r.id} photos={photo_count} score={r.score}"))
                self.stdout.write("----- OLD -----")
                self.stdout.write(old or "(empty)")
                self.stdout.write("----- NEW -----")
                self.stdout.write(new_text)
                self.stdout.write("")
            else:
                r.review_text = new_text
                to_save.append(r)

            changed += 1

        # バックアップ保存（ディレクトリ自動作成）
        if backup_path:
            payload = {
                "generated_at": timezone.now().isoformat(),
                "dry_run": dry_run,
                "seen": seen,
                "changed": changed,
                "rows": backup_rows,
            }

            backup_dir = os.path.dirname(backup_path)
            if backup_dir:
                os.makedirs(backup_dir, exist_ok=True)

            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"Backup written: {backup_path}"))

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY-RUN done. seen={seen}, changed={changed}"))
            return

        if not to_save:
            self.stdout.write(self.style.SUCCESS(f"No updates. seen={seen}, changed={changed}"))
            return

        with transaction.atomic():
            for obj in to_save:
                obj.save(update_fields=["review_text"])

        self.stdout.write(self.style.SUCCESS(f"Updated. seen={seen}, changed={changed}"))
