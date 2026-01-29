from __future__ import annotations

import re
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction

from commons.models import Store, Genre


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("　", " ")
    return s


def guess_genre_name(store: Store) -> str:
    """
    Store.genre / store_name から customer_genre_list のジャンル名へ寄せる
    できるだけ「当たりやすいものを先に」判定
    """
    g = _norm(store.genre)
    name = _norm(store.store_name)

    text = f"{g} {name}"

    # 優先度高（キーワードが明確）
    if any(k in text for k in ["鮨", "すし", "寿司", "海鮮", "回転寿司", "ふぐ", "かに", "蟹"]):
        return "寿司・海鮮"

    if any(k in text for k in ["焼肉", "ホルモン", "ジンギスカン", "bbq", "バーベキュー"]):
        return "焼肉・ホルモン"

    if any(k in text for k in ["ラーメン", "らぁ麺", "つけ麺", "まぜそば", "担々麺", "刀削麺"]):
        return "ラーメン・麺専門店"

    if any(k in text for k in ["カフェ", "喫茶", "coffee", "cafe", "珈琲", "ティー"]):
        return "カフェ・喫茶店"

    if any(k in text for k in ["中華", "餃子", "点心", "飲茶", "四川", "広東", "上海"]):
        return "中華料理"

    if any(k in text for k in ["韓国", "サムギョプサル", "冷麺", "チゲ"]):
        return "韓国料理"

    if any(k in text for k in ["タイ", "ベトナム", "インドネシア", "中東", "メキシコ", "エスニック", "アジア料理"]):
        return "アジア・エスニック"

    if "カレー" in text:
        return "カレー"

    if any(k in text for k in ["鍋", "もつ鍋", "水炊き", "火鍋", "ちゃんこ"]):
        return "鍋料理"

    if any(k in text for k in ["バー", "pub", "パブ", "ワインバー", "ビアバー"]):
        return "バー・パブ"

    if any(k in text for k in ["居酒屋", "ダイニングバー", "立ち飲み", "バル", "肉バル"]):
        return "居酒屋・ダイニングバー"

    if any(k in text for k in ["ビアガーデン", "ビアホール"]):
        return "ビアガーデン・ホール"

    if any(k in text for k in ["パン", "ベーカリー", "サンド", "サンドイッチ"]):
        return "パン・サンドイッチ"

    if any(k in text for k in ["スイーツ", "ケーキ", "パフェ", "和菓子", "大福", "かき氷", "アイス"]):
        return "スイーツ・和菓子"

    # 洋食系
    if any(k in text for k in ["イタリア", "トラットリア", "ピザ", "パスタ", "フレンチ", "ビストロ"]):
        return "イタリアン・フレンチ"

    if any(k in text for k in ["ステーキ", "鉄板焼", "ハンバーグ", "オムライス", "洋食"]):
        return "洋食・ステーキ"

    if any(k in text for k in ["スペイン", "ドイツ", "ロシア", "アメリカ", "ハンバーガー"]):
        return "各国料理(欧米)"

    # 和食系（細かい分類は決め打ち寄せ）
    if any(k in text for k in ["うなぎ", "あなご", "すき焼き", "しゃぶしゃぶ", "牛タン"]):
        return "うなぎ・肉料理(和)"

    if any(k in text for k in ["天ぷら", "とんかつ", "串揚げ", "からあげ"]):
        return "天ぷら・揚げ物"

    if any(k in text for k in ["焼き鳥", "串焼", "もつ焼", "手羽先", "鳥料理"]):
        return "焼き鳥・鳥料理"

    if any(k in text for k in ["そば", "うどん", "ほうとう", "ちゃんぽん", "焼きそば"]):
        return "そば・うどん・麺"

    if any(k in text for k in ["丼", "牛丼", "親子丼", "天丼", "かつ丼", "海鮮丼", "お好み焼き", "もんじゃ", "たこ焼き", "おでん"]):
        return "丼・お好み焼き・おでん"

    # ここまで来たら「和食っぽい」なら懐石に寄せる
    if any(k in text for k in ["和食", "懐石", "割烹", "小料理", "会席", "日本料理"]):
        return "日本料理・懐石"

    # 最後：その他へ
    return "その他施設"


class Command(BaseCommand):
    help = "Store.genre / store_name から Genre(マスタ) を推定して store.genre_master を一括更新します"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="保存せず表示のみ")
        parser.add_argument("--limit", type=int, default=0, help="テスト用：先頭N件のみ（0=全件）")
        parser.add_argument("--force", action="store_true", help="既にgenre_masterが入っていても上書きする")

    @transaction.atomic
    def handle(self, *args, **opts):
        dry_run: bool = opts["dry_run"]
        limit: int = opts["limit"]
        force: bool = opts["force"]

        # Genreを辞書化
        genre_map = {g.name: g for g in Genre.objects.all()}

        # もし seed_genres が未実行で足りない場合に備え、存在しないものは作る
        def get_or_create_genre(name: str) -> Genre:
            obj = genre_map.get(name)
            if obj:
                return obj
            obj, _ = Genre.objects.get_or_create(name=name)
            genre_map[name] = obj
            return obj

        qs = Store.objects.all().order_by("id")
        if limit and limit > 0:
            qs = qs[:limit]

        updated = 0
        skipped = 0

        for store in qs:
            if store.genre_master_id and not force:
                skipped += 1
                continue

            target_name = guess_genre_name(store)
            target = get_or_create_genre(target_name)

            before = store.genre_master.name if store.genre_master_id else "-"
            self.stdout.write(
                f"[Store id={store.id}] {store.store_name} / genre='{store.genre}' : {before} -> {target.name}"
            )

            if not dry_run:
                store.genre_master = target
                store.save(update_fields=["genre_master"])
            updated += 1

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("DRY-RUN: ロールバックしました"))
            return

        self.stdout.write(self.style.SUCCESS(f"完了: update={updated} / skip={skipped}"))
