from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import time
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


# ==========================
# 追加：ジャンル別プロファイル（電話/営業時間/席数/予算）
# ==========================
@dataclass(frozen=True)
class StoreProfile:
    business_hours: str
    open_time_1: time | None
    close_time_1: time | None
    open_time_2: time | None
    close_time_2: time | None
    seats_min: int
    seats_max: int
    budget_min: int
    budget_max: int


PROFILES: dict[str, StoreProfile] = {
    "washoku": StoreProfile(
        business_hours="11:00〜14:30 / 17:00〜22:00",
        open_time_1=time(11, 0), close_time_1=time(14, 30),
        open_time_2=time(17, 0), close_time_2=time(22, 0),
        seats_min=20, seats_max=80,
        budget_min=3000, budget_max=12000,
    ),
    "sushi": StoreProfile(
        business_hours="11:30〜14:00 / 17:00〜21:30",
        open_time_1=time(11, 30), close_time_1=time(14, 0),
        open_time_2=time(17, 0), close_time_2=time(21, 30),
        seats_min=8, seats_max=30,
        budget_min=5000, budget_max=20000,
    ),
    "chinese": StoreProfile(
        business_hours="11:00〜15:00 / 17:00〜23:00",
        open_time_1=time(11, 0), close_time_1=time(15, 0),
        open_time_2=time(17, 0), close_time_2=time(23, 0),
        seats_min=30, seats_max=120,
        budget_min=2000, budget_max=6000,
    ),
    "western": StoreProfile(
        business_hours="11:30〜15:00 / 17:30〜22:00",
        open_time_1=time(11, 30), close_time_1=time(15, 0),
        open_time_2=time(17, 30), close_time_2=time(22, 0),
        seats_min=20, seats_max=90,
        budget_min=2500, budget_max=9000,
    ),
    "yakiniku": StoreProfile(
        business_hours="17:00〜24:00",
        # 日跨ぎ用：open > close の形にしておく（あなたの検索ロジックがこれを日跨ぎとして扱う）
        open_time_1=time(17, 0), close_time_1=time(0, 0),
        open_time_2=None, close_time_2=None,
        seats_min=30, seats_max=150,
        budget_min=3500, budget_max=9000,
    ),
    "ramen": StoreProfile(
        business_hours="11:00〜15:00 / 17:00〜21:00",
        open_time_1=time(11, 0), close_time_1=time(15, 0),
        open_time_2=time(17, 0), close_time_2=time(21, 0),
        seats_min=10, seats_max=45,
        budget_min=800, budget_max=1500,
    ),
    "cafe": StoreProfile(
        business_hours="08:00〜18:00",
        open_time_1=time(8, 0), close_time_1=time(18, 0),
        open_time_2=None, close_time_2=None,
        seats_min=15, seats_max=70,
        budget_min=800, budget_max=2500,
    ),
    "other": StoreProfile(
        business_hours="11:00〜22:00",
        open_time_1=time(11, 0), close_time_1=time(22, 0),
        open_time_2=None, close_time_2=None,
        seats_min=20, seats_max=100,
        budget_min=1000, budget_max=6000,
    ),
}


def pick_profile(genre_key: str) -> StoreProfile:
    return PROFILES.get(genre_key, PROFILES["other"])


def deterministic_int(seed: int, low: int, high: int) -> int:
    """store.id から毎回同じ値が出るようにする（再実行してもブレない）"""
    if high < low:
        low, high = high, low
    span = (high - low) + 1
    return low + (seed % span)


def make_seats(store: Store, prof: StoreProfile) -> int:
    return deterministic_int((store.id or 1) * 31, prof.seats_min, prof.seats_max)


def make_budget(store: Store, prof: StoreProfile) -> int:
    return deterministic_int((store.id or 1) * 97, prof.budget_min, prof.budget_max)


def guess_phone_prefix(area_name: str) -> str:
    a = (area_name or "").strip()
    if "東京都" in a:
        return "03"
    if "大阪府" in a:
        return "06"
    if "北海道" in a:
        return "011"
    if "愛知県" in a:
        return "052"
    if "福岡県" in a:
        return "092"
    # その他は “代表番号っぽく” 050 に寄せる
    return "050"


def make_phone_number(store: Store) -> str:
    area_name = ""
    try:
        area_name = store.area.area_name
    except Exception:
        area_name = ""

    prefix = guess_phone_prefix(area_name)

    # 8桁部分をIDから作る（例: 12345678）
    n = ((store.id or 1) * 123457) % 100000000
    s = f"{n:08d}"

    # 03/06 は 4-4、それ以外(3桁市外局番)は 3-4 っぽく
    if prefix in ("03", "06"):
        return f"{prefix}-{s[:4]}-{s[4:]}"
    else:
        # 050/011/052/092 など
        return f"{prefix}-{s[:3]}-{s[3:7]}"


class Command(BaseCommand):
    help = (
        "全Storeの店舗名/支店名/email をジャンルに合わせて一括リネームし、"
        "紐づくStoreAccountのemail/admin_emailも更新します（UNIQUE衝突回避）。"
        "さらに電話番号/営業時間/席数/予算/open-closeもジャンルに合わせて更新します。"
    )

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

            prof = pick_profile(genre_key)
            new_phone = make_phone_number(store)
            new_hours = prof.business_hours
            new_seats = make_seats(store, prof)
            new_budget = make_budget(store, prof)
            new_open1, new_close1 = prof.open_time_1, prof.close_time_1
            new_open2, new_close2 = prof.open_time_2, prof.close_time_2

            if (
                store.store_name != new_name or
                store.branch_name != new_branch or
                (store.email or "").lower() != new_store_email or
                (store.phone_number or "") != new_phone or
                (store.business_hours or "") != new_hours or
                (store.seats or 0) != new_seats or
                (store.budget or 0) != new_budget or
                store.open_time_1 != new_open1 or
                store.close_time_1 != new_close1 or
                store.open_time_2 != new_open2 or
                store.close_time_2 != new_close2
            ):
                self.stdout.write(
                    f"[Store id={store.id}] "
                    f"name '{store.store_name}'→'{new_name}' / "
                    f"branch '{store.branch_name}'→'{new_branch}' / "
                    f"email '{store.email}'→'{new_store_email}' / "
                    f"phone '{store.phone_number}'→'{new_phone}' / "
                    f"hours '{store.business_hours}'→'{new_hours}' / "
                    f"seats {store.seats}→{new_seats} / "
                    f"budget {store.budget}→{new_budget}"
                )
                if not dry_run:
                    store.store_name = new_name
                    store.branch_name = new_branch
                    store.email = new_store_email
                    store.phone_number = new_phone
                    store.business_hours = new_hours
                    store.seats = new_seats
                    store.budget = new_budget
                    store.open_time_1 = new_open1
                    store.close_time_1 = new_close1
                    store.open_time_2 = new_open2
                    store.close_time_2 = new_close2

                    store.save(update_fields=[
                        "store_name", "branch_name", "email",
                        "phone_number", "business_hours", "seats", "budget",
                        "open_time_1", "close_time_1", "open_time_2", "close_time_2",
                    ])
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
