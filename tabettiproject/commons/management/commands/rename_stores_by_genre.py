from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction

from commons.models import Store, StoreAccount, Account


# ==========================
# ジャンル判定（ゆるめに）
# ==========================
def normalize_genre(g: str) -> str:
    g = (g or "").strip()

    if "寿司" in g or "海鮮" in g:
        return "sushi"
    if "焼肉" in g or "ホルモン" in g:
        return "yakiniku"
    if "ラーメン" in g or "麺" in g:
        return "ramen"
    if "カフェ" in g or "喫茶" in g:
        return "cafe"
    if "中華" in g or "餃子" in g or "四川" in g:
        return "chinese"
    if "イタリア" in g or "フレンチ" in g or "洋食" in g or "ステーキ" in g:
        return "western"
    if "和食" in g or "懐石" in g or "天ぷら" in g or "そば" in g or "うどん" in g:
        return "washoku"

    if g == "和食":
        return "washoku"
    if g == "洋食":
        return "western"
    if g == "中華":
        return "chinese"
    if g == "焼肉":
        return "yakiniku"
    if g == "カフェ":
        return "cafe"

    return "other"


# ==========================
# 住所から「地名っぽい部分」を抜く
# ==========================
CITY_RE = re.compile(r"(?:都|道|府|県).+?(?:市|区|町|村)")

def guess_place_from_address(address: str) -> str:
    addr = (address or "").strip()
    if not addr:
        return ""
    m = CITY_RE.search(addr)
    if m:
        return m.group(0)
    return addr[:12]


# ==========================
# 店名生成
# ==========================
@dataclass(frozen=True)
class NameSpec:
    bases: tuple[str, ...]
    suffixes: tuple[str, ...]
    prefix: str = ""


NAME_SPECS: dict[str, NameSpec] = {
    "washoku": NameSpec(
        bases=("季彩堂", "柚庵", "花乃", "山吹", "千歳", "雅", "小春", "凪", "若竹", "こだま"),
        suffixes=("庵", "亭", "料理店", "食事処", "割烹"),
        prefix="和食",
    ),
    "sushi": NameSpec(
        bases=("銀波", "白金", "青海", "千寿", "蒼", "潮", "匠", "一心", "松風", "汐彩"),
        suffixes=("鮨", "寿司", "寿司処", "鮨処"),
        prefix="",
    ),
    "chinese": NameSpec(
        bases=("龍彩堂", "華彩堂", "金華", "翠彩堂", "福彩堂", "大福", "香彩堂", "紅彩堂", "鳳凰", "聚彩堂"),
        suffixes=("飯店", "楼", "中華", "中華厨房", "餃子坊"),
        prefix="",
    ),
    "western": NameSpec(
        bases=("ルーチェ", "ソレイユ", "ビアンカ", "オリーヴァ", "グラース", "ノスタル", "ベル", "リーヴ", "モンターニュ", "エトワール"),
        suffixes=("キッチン", "ダイニング", "ビストロ", "トラットリア", "レストラン"),
        prefix="",
    ),
    "yakiniku": NameSpec(
        bases=("炭彩堂", "炎彩堂", "黒彩堂", "金彩堂", "匠彩堂", "和彩堂", "赤彩堂", "極", "焔", "燈"),
        suffixes=("焼肉", "炭火焼肉", "ホルモン", "焼肉処"),
        prefix="",
    ),
    "ramen": NameSpec(
        bases=("麺彩堂", "一麺", "麺匠", "麺屋", "麺道", "白湯", "極麺", "麺工房", "麺房", "らぁ麺"),
        suffixes=("本舗", "処", "亭", "店", "屋"),
        prefix="",
    ),
    "cafe": NameSpec(
        bases=("茶彩堂", "小径", "木の実", "陽だまり", "そよ風", "白樺", "月灯り", "うたたね", "森の", "ひだまり"),
        suffixes=("カフェ", "喫茶", "茶房", "Coffee", "CAFE"),
        prefix="",
    ),
    "other": NameSpec(
        bases=("タベッチ", "まちの", "ひより", "こもれび", "まる", "つむぎ", "うらら", "つばき", "さくら", "あおい"),
        suffixes=("食堂", "ダイニング", "キッチン", "亭", "店"),
        prefix="",
    ),
}

def make_store_name(store: Store) -> str:
    genre_key = normalize_genre(store.genre)
    spec = NAME_SPECS.get(genre_key, NAME_SPECS["other"])

    base = spec.bases[(store.id or 1) % len(spec.bases)]
    suf = spec.suffixes[(store.id or 1) % len(spec.suffixes)]

    if spec.prefix:
        name = f"{spec.prefix} {base}{suf}"
    else:
        name = f"{base}{suf}"

    return name[:100]


def make_branch_name(store: Store, place: str) -> str:
    area_name = ""
    try:
        area_name = (store.area.area_name or "").strip()
    except Exception:
        area_name = ""

    p = (place or "").strip() or area_name
    if not p:
        return "本店"

    if p.endswith("店"):
        return p[:100]
    return f"{p}店"[:100]


# ==========================
# email のユニーク確保
# ==========================
def ensure_unique_email(local_base: str, domain: str, exclude_account_pk: Optional[int] = None) -> str:
    """
    local_base + @domain が既に存在する場合、-2, -3... を付けて空きを探す
    exclude_account_pk: 自分自身の更新なら自分は除外
    """
    local_base = re.sub(r"[^a-zA-Z0-9\-_\.]+", "-", (local_base or "").strip())
    local_base = local_base.strip("-._").lower()
    if not local_base:
        local_base = "user"

    def exists(email: str) -> bool:
        qs = Account.objects.filter(email__iexact=email)
        if exclude_account_pk is not None:
            qs = qs.exclude(pk=exclude_account_pk)
        return qs.exists()

    # まず素のまま
    email = f"{local_base}@{domain}".lower()[:255]
    if not exists(email):
        return email

    # 衝突したら suffix
    for i in range(2, 10000):
        e = f"{local_base}-{i}@{domain}".lower()
        e = e[:255]
        if not exists(e):
            return e

    # ほぼ起きないが保険
    raise RuntimeError("email の空きが見つかりませんでした（異常に衝突しています）")


def make_store_email(store: Store, genre_key: str, domain: str) -> str:
    # 店舗の連絡先（店舗ごとに1つ）
    local = f"info-{genre_key}-{store.id}"
    # Store.email は unique じゃないけど、衝突しないようにユニーク化しておく
    return ensure_unique_email(local, domain, exclude_account_pk=None)


def make_store_account_email(store: Store, acc: StoreAccount, genre_key: str, domain: str) -> str:
    # ログイン用（アカウントごとに必ずユニーク）
    local = f"admin-{genre_key}-{store.id}-{acc.pk}"
    return ensure_unique_email(local, domain, exclude_account_pk=acc.pk)


class Command(BaseCommand):
    help = "全Storeの店舗名/支店名/emailをジャンルに合わせて一括リネームし、紐づくStoreAccountのemail/admin_emailも更新します（UNIQUE衝突回避）。"

    def add_arguments(self, parser):
        parser.add_argument("--domain", type=str, default="tabetti.example")
        parser.add_argument("--dry-run", action="store_true", help="DBを更新せず、変更内容だけ表示")
        parser.add_argument("--limit", type=int, default=0, help="テスト用：先頭N件だけ処理（0=全件）")

    @transaction.atomic
    def handle(self, *args, **opt):
        domain: str = opt["domain"]
        dry_run: bool = opt["dry_run"]
        limit: int = opt["limit"]

        qs = Store.objects.select_related("area").order_by("id")
        if limit and limit > 0:
            qs = qs[:limit]

        updated_store = 0
        updated_accounts = 0

        for store in qs:
            genre_key = normalize_genre(store.genre)
            place = guess_place_from_address(store.address)

            new_name = make_store_name(store)
            new_branch = make_branch_name(store, place)
            new_store_email = make_store_email(store, genre_key, domain)

            if (
                store.store_name != new_name or
                store.branch_name != new_branch or
                (store.email or "").lower() != new_store_email
            ):
                self.stdout.write(
                    f"[Store id={store.id}] "
                    f"'{store.store_name}'→'{new_name}' / "
                    f"'{store.branch_name}'→'{new_branch}' / "
                    f"'{store.email}'→'{new_store_email}'"
                )
                if not dry_run:
                    store.store_name = new_name
                    store.branch_name = new_branch
                    store.email = new_store_email
                    store.save(update_fields=["store_name", "branch_name", "email"])
                updated_store += 1

            # StoreAccount 側：emailは必ずユニークに（アカウント単位）
            acc_qs = StoreAccount.objects.filter(store=store).order_by("id")
            for acc in acc_qs:
                new_acc_email = make_store_account_email(store, acc, genre_key, domain)

                # admin_email は「店舗の代表メール」に寄せる（unique制約なし）
                new_admin_email = new_store_email

                if (acc.email or "").lower() != new_acc_email or (acc.admin_email or "").lower() != new_admin_email:
                    self.stdout.write(
                        f"  [StoreAccount id={acc.id}] email '{acc.email}'→'{new_acc_email}' / admin_email '{acc.admin_email}'→'{new_admin_email}'"
                    )
                    if not dry_run:
                        acc.email = new_acc_email
                        acc.admin_email = new_admin_email
                        acc.save(update_fields=["email", "admin_email"])
                    updated_accounts += 1

        if dry_run:
            # atomic の中で rollback したいので明示
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("DRY-RUN: 変更は保存していません（ロールバック）"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"完了: Store更新={updated_store}件 / StoreAccount更新={updated_accounts}件"
        ))
