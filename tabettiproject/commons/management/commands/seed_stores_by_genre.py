from __future__ import annotations

import random
import re
from datetime import time
from typing import Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from commons.models import Store, Genre, Area, Scene


def _slugify(text: str) -> str:
    s = text.strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^\w\-ぁ-んァ-ン一-龥]", "", s)
    return s[:30] if s else "genre"


def _pick_hours(genre_name: str) -> Tuple[str, time, time, time | None, time | None]:
    """
    genreに合わせて営業時間っぽい値を返す
    business_hours, open_time_1, close_time_1, open_time_2, close_time_2
    """
    # 深夜寄り
    late = ["居酒屋", "バー", "ビア"]
    if any(k in genre_name for k in late):
        # 17-01
        return ("17:00-01:00", time(17, 0), time(1, 0), None, None)

    # ラーメン系は通し営業っぽく
    if "ラーメン" in genre_name:
        return ("11:00-22:00", time(11, 0), time(22, 0), None, None)

    # カフェ・パン・スイーツ
    if any(k in genre_name for k in ["カフェ", "喫茶", "パン", "スイーツ", "和菓子"]):
        return ("09:00-18:00", time(9, 0), time(18, 0), None, None)

    # 基本：ランチ/ディナー二部制
    return ("11:00-15:00 / 17:00-22:00", time(11, 0), time(15, 0), time(17, 0), time(22, 0))


def _pick_budget_seats(genre_name: str) -> Tuple[int, int]:
    """
    (budget, seats) を genre に合わせてざっくり作る
    """
    if any(k in genre_name for k in ["懐石", "寿司", "うなぎ"]):
        budget = random.randint(6000, 20000)
        seats = random.randint(10, 40)
        return budget, seats

    if any(k in genre_name for k in ["焼肉", "ステーキ", "鍋"]):
        budget = random.randint(3500, 12000)
        seats = random.randint(20, 80)
        return budget, seats

    if any(k in genre_name for k in ["居酒屋", "ダイニング", "ビア"]):
        budget = random.randint(2500, 7000)
        seats = random.randint(30, 120)
        return budget, seats

    if any(k in genre_name for k in ["バー", "パブ"]):
        budget = random.randint(3000, 9000)
        seats = random.randint(10, 35)
        return budget, seats

    if any(k in genre_name for k in ["カフェ", "喫茶", "パン", "スイーツ", "和菓子"]):
        budget = random.randint(800, 2500)
        seats = random.randint(10, 50)
        return budget, seats

    if "ラーメン" in genre_name:
        budget = random.randint(800, 1800)
        seats = random.randint(8, 30)
        return budget, seats

    # デフォルト
    budget = random.randint(1200, 6000)
    seats = random.randint(12, 70)
    return budget, seats


def _name_templates(genre_name: str) -> Tuple[list[str], list[str]]:
    """
    店舗名のテンプレと支店名候補
    """
    base_names = {
        "日本料理": ["和ごころ", "四季彩堂", "小料理 みやび", "京の膳", "味彩堂"],
        "寿司": ["鮨 はな", "鮨 しお", "鮨 みさき", "海の幸 すし処", "江戸前 鮨匠"],
        "うなぎ": ["うなぎ うな匠", "鰻 しらかわ", "うな重本舗", "鰻の匠", "蒲焼き 竹"],
        "天ぷら": ["天ぷら さくら", "天冨良 いち", "天ぷら 風", "天ぷら 山", "天ぷら 匠"],
        "焼き鳥": ["焼鳥 とり勢", "炭火焼鳥 しん", "焼鳥 かしわ", "鳥料理 たけ", "焼鳥 まる"],
        "そば": ["手打ちそば 風月", "そば処 みのり", "蕎麦 玄", "うどん庵", "麺彩堂"],
        "丼": ["丼の里", "お好み焼き まる", "もんじゃ 鉄", "おでん亭", "海鮮丼 みなと"],
        "イタリアン": ["Trattoria Luna", "Osteria Sole", "Pizzeria Mare", "Bistro Fiore", "Ristorante Azzurro"],
        "洋食": ["洋食屋 キッチン光", "グリル銀河", "ハンバーグ工房", "オムライス亭", "鉄板グリル匠"],
        "各国料理": ["スペインバル Sol", "ドイツ食堂 BierHaus", "アメリカンダイナー Route", "ロシア料理 白夜", "タパス食堂"],
        "中華": ["中華楼 龍", "四川飯店 花椒", "広東酒家 福", "上海小籠包 霞", "飲茶茶楼"],
        "韓国": ["韓国食堂 ましっそ", "サムギョプサル亭", "韓国屋台 ハン", "冷麺房", "韓国料理 ソウル"],
        "アジア": ["タイ食堂 サワディ", "ベトナム屋台 フォー", "インドカレー苑", "中東料理 アラビアン", "エスニックバル"],
        "カレー": ["咖喱屋 スパイス", "欧風カレー ふくろう", "スープカレー ひまわり", "印度カレー ルビー", "カレー食堂"],
        "焼肉": ["焼肉 ぎゅう丸", "ホルモン道場", "焼肉 炎", "焼肉 たん匠", "炭火焼肉 匠"],
        "鍋": ["もつ鍋 もつ蔵", "水炊き しろ", "ちゃんこ 鍋力", "火鍋 麻辣", "鍋料理 まる"],
        "ラーメン": ["らーめん一番", "麺屋 しん", "濃厚豚骨 麺魂", "味噌らーめん 鐵", "つけ麺工房"],
        "居酒屋": ["居酒屋 まる", "立ち飲み 角", "バル酒場", "大衆酒場 たぬき", "ダイニング 炭"],
        "バー": ["Bar Nocturne", "Wine Bar Lien", "Pub Clover", "Bar Atlas", "Cocktail Bar Echo"],
        "ビア": ["Beer Hall Hop", "ビアガーデン 風", "クラフトビア うた", "ビアホール 樽", "Hop & Malt"],
        "カフェ": ["Cafe 窓辺", "喫茶 こもれび", "Coffee Stand", "Cafe Haru", "喫茶 雫"],
        "パン": ["ベーカリー こむぎ", "サンド工房", "パンの家", "ブーランジェリー", "ベーカリー まる"],
        "スイーツ": ["スイーツ工房", "和菓子処 つき", "ケーキの森", "甘味処 花", "パフェ専門店"],
        "レストラン": ["レストラン ひなた", "食堂 みなと", "ファミリーレストラン", "ビュッフェ そら", "オーガニック食堂"],
        "その他": ["道の駅キッチン", "ホテルダイニング", "屋形船 みず", "カラオケ＆ダイニング", "施設レストラン"],
    }

    # キーに近いものを拾う（ざっくり）
    pick = []
    for k, v in base_names.items():
        if k in genre_name:
            pick = v
            break
    if not pick:
        pick = ["食彩堂", "味の蔵", "ごはん処", "食事処", "美味亭"]

    branches = ["本店", "駅前店", "中央店", "西口店", "東口店", "南店", "北店", "新町店", "桜通り店", "一番街店"]
    return pick, branches


class Command(BaseCommand):
    help = "各ジャンル(Genre)につき最低N件の店舗(Store)を自動生成します（足りない分だけ追加）"

    def add_arguments(self, parser):
        parser.add_argument("--per-genre", type=int, default=10, help="各ジャンル最低何件にするか（デフォルト10）")
        parser.add_argument("--dry-run", action="store_true", help="DBに保存せず、作成予定だけ表示")
        parser.add_argument("--seed", type=int, default=1234, help="乱数シード（デフォルト1234）")

    @transaction.atomic
    def handle(self, *args, **options):
        per_genre: int = options["per_genre"]
        dry_run: bool = options["dry_run"]
        seed: int = options["seed"]

        random.seed(seed)

        genres = list(Genre.objects.all())
        if not genres:
            self.stderr.write(self.style.ERROR("Genre が0件です。先にGenreを登録してください。"))
            return

        areas = list(Area.objects.all())
        if not areas:
            self.stderr.write(self.style.ERROR("Area が0件です。先にAreaを登録してください。"))
            return

        scenes = list(Scene.objects.all())
        if not scenes:
            self.stderr.write(self.style.ERROR("Scene が0件です。先にSceneを登録してください。"))
            return

        total_to_create = 0

        for genre in genres:
            existing = Store.objects.filter(genre_master=genre).count()
            need = max(0, per_genre - existing)
            if need <= 0:
                self.stdout.write(f"✓ {genre.name}: 既に {existing} 件（追加なし）")
                continue

            total_to_create += need
            self.stdout.write(f"→ {genre.name}: {existing} 件 → 追加 {need} 件")

            base_names, branches = _name_templates(genre.name)
            bh, o1, c1, o2, c2 = _pick_hours(genre.name)

            for i in range(need):
                area = random.choice(areas)
                scene = random.choice(scenes)
                budget, seats = _pick_budget_seats(genre.name)

                store_base = random.choice(base_names)
                branch = random.choice(branches)

                # 既存と被りにくくするため suffix を付与
                suffix = random.randint(100, 999)
                store_name = f"{store_base}{suffix}"
                branch_name = branch

                # ダミーだけどそれっぽい住所（Area名を先頭に入れる）
                addr_city = random.choice(["中央", "新町", "桜台", "本町", "栄町", "駅前", "南町", "北町"])
                addr = f"{area.area_name}{addr_city}1-2-{random.randint(1, 99)}"

                # 地図（必須なのでダミー文字列）
                map_location = f"POINT({random.uniform(130, 140):.6f} {random.uniform(33, 36):.6f})"

                # 連絡先
                email = f"{_slugify(genre.name)}-{random.randint(10000, 99999)}@example.com"
                phone = f"0{random.randint(1,9)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}"

                # genre文字列は keyword 検索で使うので master名と同じにしておく
                store = Store(
                    store_name=store_name,
                    branch_name=branch_name,
                    email=email,
                    phone_number=phone,
                    address=addr,
                    map_location=map_location,
                    area=area,
                    business_hours=bh,
                    open_time_1=o1,
                    close_time_1=c1,
                    open_time_2=o2,
                    close_time_2=c2,
                    seats=seats,
                    budget=budget,
                    genre=genre.name,
                    genre_master=genre,
                    scene=scene,
                    reservable=True,
                    editable=True,
                )

                if dry_run:
                    self.stdout.write(f"  [DRY] {genre.name} / {store_name} {branch_name} / {area.area_name} / {bh}")
                else:
                    store.save()

        if dry_run:
            # dry-run はロールバックさせたいので例外で止めるのもアリだが、
            # ここでは保存してないのでそのまま終了
            self.stdout.write(self.style.WARNING(f"DRY-RUN 完了（作成予定: {total_to_create} 件）"))
        else:
            self.stdout.write(self.style.SUCCESS(f"完了: 作成 {total_to_create} 件（各ジャンル最低 {per_genre} 件）"))
