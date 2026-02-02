from __future__ import annotations

import hashlib
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from commons.models import Account, CustomerAccount


EXCLUDE_IDS = {18, 21, 1167}


def _is_username_like(u: str) -> bool:
    """すでに username っぽいなら（forceなしで）スキップする判定"""
    u = (u or "").strip().lower()
    return bool(re.fullmatch(r"[a-z0-9_]{3,50}", u))


def _make_unique_username(base: str, taken: set[str]) -> str:
    cand = base
    if cand not in taken:
        return cand
    i = 2
    while True:
        suffix = f"_{i}"
        head = base[: max(1, 50 - len(suffix))]
        cand = f"{head}{suffix}"
        if cand not in taken:
            return cand
        i += 1


# ===== ニックネーム生成（安全な語彙だけを使用） =====
GOURMET_STYLE = [
    "食べ歩き", "予約戦士", "酒場通い", "名店ハンター", "町中華研究",
    "鮨目利き", "蕎麦探訪", "焼鳥審査", "ラーメン探求", "カレー巡礼",
    "甘味巡り", "珈琲偏愛", "和食の道", "発酵好き", "出汁こだわり",
    "粉もの推し", "野菜ソムリエ", "肉の哲学", "海鮮博士", "旨辛評論",
]

GOURMET_TITLE = [
    "評論家", "探訪家", "研究家", "鑑定士", "案内人", "ソムリエ",
    "目利き", "番長", "隊長", "師範", "達人", "指南役",
]

GOURMET_EMOJI = ["🍣", "🍶", "🍜", "🥢", "🥩", "🐟", "🍷", "☕", "🍮", "🌶️", "🧂"]



def _pick_by_id(user_id: int, items: list[str], salt: str) -> str:
    """
    user_id + salt からハッシュを作り、itemsから決定的に選ぶ
    """
    src = f"{salt}:{user_id}".encode("utf-8")
    h = hashlib.sha256(src).hexdigest()
    n = int(h[:8], 16)  # 32bit分で十分
    return items[n % len(items)]


def _generate_fun_nickname(user_id: int) -> str:
    """
    例:
    - "鮨目利き鑑定士（カウンター席）🍣"
    - "町中華研究指南役（路地裏）🥟" ←（🥟が欲しければ絵文字候補に追加OK）
    """
    style = _pick_by_id(user_id, GOURMET_STYLE, "g_style")
    title = _pick_by_id(user_id, GOURMET_TITLE, "g_title")
    emoji = _pick_by_id(user_id, GOURMET_EMOJI, "g_emoji")

    return f"{style}{title}{emoji}"

def _make_unique_nickname(base: str, taken: set[str], user_id: int) -> str:
    """
    nickname はユニーク制約が無い想定だけど、管理の見やすさのため衝突回避する
    """
    if base not in taken:
        return base
    # 既存と被ったらIDを足してユニークに
    cand = f"{base}-{user_id}"
    return cand if cand not in taken else f"{base}-{user_id}-2"


class Command(BaseCommand):
    help = "Bulk rename CustomerAccount.username and CustomerAccount.nickname (fun nicknames)."

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="Actually update DB. Without this, dry-run.")
        parser.add_argument("--force", action="store_true", help="Rename even if username already looks username-like.")
        parser.add_argument(
            "--username-prefix",
            type=str,
            default="customer_",
            help="Prefix for username. default='customer_' -> customer_<id>",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of updates (0 = no limit). Useful for testing.",
        )

    def handle(self, *args, **options):
        commit = options["commit"]
        force = options["force"]
        username_prefix = (options["username_prefix"] or "customer_").strip()
        limit = int(options["limit"] or 0)

        # username は全Accountでユニーク
        taken_usernames = set(
            (u or "").strip().lower()
            for u in Account.objects.values_list("username", flat=True)
            if u
        )

        # nickname は CustomerAccount 内の既存を把握（重複回避のため）
        taken_nicknames = set(
            (n or "").strip()
            for n in CustomerAccount.objects.values_list("nickname", flat=True)
            if n
        )

        qs = CustomerAccount.objects.exclude(id__in=EXCLUDE_IDS).order_by("id")

        planned: list[tuple[int, str, str, str, str]] = []
        skipped = 0

        for cu in qs.iterator():
            old_username = (cu.username or "").strip()
            old_nickname = (cu.nickname or "").strip()

            if (not force) and _is_username_like(old_username):
                skipped += 1
                continue

            base_username = f"{username_prefix}{cu.id}".lower()
            new_username = _make_unique_username(base_username, taken_usernames)

            base_nickname = _generate_fun_nickname(cu.id)
            new_nickname = _make_unique_nickname(base_nickname, taken_nicknames, cu.id)

            if (new_username == old_username.lower()) and (new_nickname == old_nickname):
                skipped += 1
                continue

            planned.append((cu.id, old_username, new_username, old_nickname, new_nickname))
            taken_usernames.add(new_username)
            taken_nicknames.add(new_nickname)

            if limit and len(planned) >= limit:
                break

        if not planned:
            self.stdout.write(self.style.SUCCESS("No customer accounts to rename."))
            return

        self.stdout.write("Planned changes (CustomerAccount):")
        for cid, ou, nu, on, nn in planned[:200]:
            self.stdout.write(f"  id={cid}: username {ou!r} -> {nu!r} | nickname {on!r} -> {nn!r}")
        if len(planned) > 200:
            self.stdout.write(f"  ... and {len(planned) - 200} more")

        self.stdout.write(f"Excluded IDs: {sorted(EXCLUDE_IDS)}")

        if not commit:
            self.stdout.write(self.style.WARNING("Dry-run finished. Add --commit to apply changes."))
            self.stdout.write(self.style.WARNING("Example: python manage.py rename_customer_accounts --commit"))
            return

        with transaction.atomic():
            for cid, _ou, nu, _on, nn in planned:
                # 親(Account)のusername と 子(CustomerAccount)のnickname を更新
                Account.objects.filter(id=cid).update(username=nu)
                CustomerAccount.objects.filter(id=cid).update(nickname=nn)

        self.stdout.write(self.style.SUCCESS(f"Done. Renamed {len(planned)} customer accounts. Skipped {skipped}."))
