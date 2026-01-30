from __future__ import annotations

import hashlib
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from commons.models import CustomerAccount


# CustomerAccount の定義と一致させる
DEFAULT_ICON = "customer/icon/default_cover.jpg"
DEFAULT_COVER = "customer/cover/default_cover.jpg"


def pick_deterministic(files: list[Path], key: str) -> Path:
    """seed+account.id から決定的に1枚選ぶ（毎回同じ割当）"""
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    idx = int(h[:8], 16) % len(files)
    return files[idx]


def list_files(dir_path: Path) -> list[Path]:
    if not dir_path.exists():
        return []
    # 画像っぽい拡張子だけ拾う（不要なら外してOK）
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    return sorted([p for p in dir_path.glob("*") if p.is_file() and p.suffix.lower() in exts])


class Command(BaseCommand):
    help = "CustomerAccount の icon_image / cover_image を media/_pool から一括付与（defaultの人だけ置換）"

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=str, default="20260130", help="割当の再現用seed")
        parser.add_argument("--force", action="store_true", help="default以外も上書き")
        parser.add_argument("--icon-only", action="store_true", help="icon_image のみ処理")
        parser.add_argument("--cover-only", action="store_true", help="cover_image のみ処理")
        parser.add_argument("--dry-run", action="store_true", help="保存せず件数だけ確認")
        parser.add_argument("--limit", type=int, default=None, help="処理上限（検証用）")

    def handle(self, *args, **opts):
        if opts["icon_only"] and opts["cover_only"]:
            raise CommandError("--icon-only と --cover-only は同時指定できません")

        # pool の場所（指定どおり）
        icon_pool = Path(settings.MEDIA_ROOT) / "_pool" / "customer" / "icon"
        cover_pool = Path(settings.MEDIA_ROOT) / "_pool" / "customer" / "cover"

        icon_files = list_files(icon_pool)
        cover_files = list_files(cover_pool)

        if not opts["cover_only"] and not icon_files:
            raise CommandError(f"icon pool が空 or 見つからない: {icon_pool}")
        if not opts["icon_only"] and not cover_files:
            raise CommandError(f"cover pool が空 or 見つからない: {cover_pool}")

        qs = CustomerAccount.objects.all().order_by("id")
        if opts["limit"]:
            qs = qs[: opts["limit"]]

        total = qs.count()
        updated = 0
        skipped = 0

        for acc in qs:
            cur_icon = (acc.icon_image.name or "")
            cur_cover = (acc.cover_image.name or "")

            need_icon = (not opts["cover_only"]) and (opts["force"] or cur_icon == DEFAULT_ICON)
            need_cover = (not opts["icon_only"]) and (opts["force"] or cur_cover == DEFAULT_COVER)

            if not need_icon and not need_cover:
                skipped += 1
                continue

            if opts["dry_run"]:
                updated += 1
                continue

            update_fields = []

            if need_icon:
                icon_path = pick_deterministic(icon_files, f"{opts['seed']}:icon:{acc.id}")
                with icon_path.open("rb") as f:
                    # 保存先は upload_to="customer/icon/" になる
                    acc.icon_image.save(icon_path.name, File(f), save=False)
                update_fields.append("icon_image")

            if need_cover:
                cover_path = pick_deterministic(cover_files, f"{opts['seed']}:cover:{acc.id}")
                with cover_path.open("rb") as f:
                    # 保存先は upload_to="customer/cover/" になる
                    acc.cover_image.save(cover_path.name, File(f), save=False)
                update_fields.append("cover_image")

            acc.save(update_fields=update_fields)
            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"対象:{total} 更新:{updated} スキップ:{skipped} seed={opts['seed']} force={opts['force']} dry_run={opts['dry_run']}"
        ))
