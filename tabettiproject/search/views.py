from __future__ import annotations

from datetime import date, datetime, timedelta

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Q
from django.shortcuts import render
from django.db import models

from commons.models import (
    Store,
    StoreAccount,
    StoreImage,
    StoreOnlineReservation,
)

# =====================================================
# ジャンル一覧（★フル版・元に戻した）
# =====================================================
def genre_list(request):
    genre_data = [
        {
            "category": "和食",
            "items": [
                {"name": "日本料理・懐石", "tags": "日本料理｜郷土料理｜豆腐料理｜料理旅館"},
                {"name": "寿司・海鮮", "tags": "寿司｜回転寿司｜海鮮｜ふぐ｜かに｜えび｜貝"},
                {"name": "うなぎ・肉料理(和)", "tags": "うなぎ｜あなご｜すき焼き｜しゃぶしゃぶ｜牛タン"},
                {"name": "天ぷら・揚げ物", "tags": "天ぷら｜とんかつ｜串揚げ｜からあげ"},
                {"name": "焼き鳥・鳥料理", "tags": "焼き鳥｜串焼き｜もつ焼き｜手羽先"},
                {"name": "そば・うどん・麺", "tags": "そば｜うどん｜ほうとう｜ちゃんぽん｜焼きそば"},
                {"name": "丼・お好み焼き・おでん", "tags": "牛丼｜親子丼｜天丼｜かつ丼｜海鮮丼｜お好み焼き｜もんじゃ｜たこ焼き｜おでん"},
            ],
        },
        {
            "category": "洋食・西洋料理",
            "items": [
                {"name": "イタリアン・フレンチ", "tags": "イタリアン｜パスタ｜ピザ｜フレンチ｜ビストロ"},
                {"name": "洋食・ステーキ", "tags": "洋食｜ハンバーグ｜オムライス｜ステーキ｜鉄板焼"},
                {"name": "各国料理(欧米)", "tags": "スペイン料理｜ドイツ料理｜ロシア料理｜アメリカ料理｜ハンバーガー"},
            ],
        },
        {
            "category": "中華・アジア・エスニック",
            "items": [
                {"name": "中華料理", "tags": "中華料理｜四川料理｜広東料理｜上海料理｜飲茶｜点心｜餃子"},
                {"name": "韓国料理", "tags": "韓国料理｜サムギョプサル｜冷麺"},
                {"name": "アジア・エスニック", "tags": "タイ料理｜ベトナム料理｜インドネシア料理｜インド料理｜中東料理｜メキシコ料理"},
            ],
        },
        {
            "category": "カレー・焼肉・鍋",
            "items": [
                {"name": "カレー", "tags": "カレー｜インドカレー｜スープカレー｜欧風カレー"},
                {"name": "焼肉・ホルモン", "tags": "焼肉｜ホルモン｜ジンギスカン｜バーベキュー"},
                {"name": "鍋料理", "tags": "もつ鍋｜水炊き｜ちゃんこ鍋｜火鍋｜うどんすき"},
            ],
        },
        {
            "category": "ラーメン・つけ麺",
            "items": [
                {"name": "ラーメン・麺専門店", "tags": "ラーメン｜つけ麺｜まぜそば｜担々麺｜刀削麺"},
            ],
        },
        {
            "category": "居酒屋・バー・お酒",
            "items": [
                {"name": "居酒屋・ダイニングバー", "tags": "居酒屋｜立ち飲み｜バル｜肉バル｜ダイニングバー"},
                {"name": "バー・パブ", "tags": "バー｜ワインバー｜ビアバー｜スポーツバー｜日本酒バー"},
                {"name": "ビアガーデン・ホール", "tags": "ビアガーデン｜ビアホール"},
            ],
        },
        {
            "category": "カフェ・パン・スイーツ",
            "items": [
                {"name": "カフェ・喫茶店", "tags": "カフェ｜喫茶店｜コーヒースタンド｜ティーパレス"},
                {"name": "パン・サンドイッチ", "tags": "パン｜サンドイッチ｜ベーカリー"},
                {"name": "スイーツ・和菓子", "tags": "ケーキ｜パフェ｜和菓子｜大福｜かき氷｜アイスクリーム"},
            ],
        },
        {
            "category": "その他・施設",
            "items": [
                {"name": "レストラン・食堂", "tags": "ファミレス｜食堂｜弁当｜惣菜｜オーガニック｜ビュッフェ"},
                {"name": "その他施設", "tags": "カラオケ｜ホテル｜道の駅｜コンビニ｜屋形船"},
            ],
        },
    ]

    return render(request, "search/customer_genre_list.html", {"genre_data": genre_data})


# =====================================================
# 検索結果（店舗一覧）
# =====================================================
def customer_search_listView(request):
    # ---------- 検索条件 ----------
    area_name = (request.GET.get("area") or "").strip()
    keyword = (request.GET.get("keyword") or "").strip()
    search_time_str = (request.GET.get("time") or "").strip()

    # カレンダー基準日
    date_str = (request.GET.get("date") or "").strip()
    try:
        base_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        base_date = date.today()

    date_list = [base_date + timedelta(days=i) for i in range(12)]

    # ---------- 店舗ベースクエリ ----------
    store_qs = (
        Store.objects
        .select_related("area", "scene")
        .annotate(
            has_account=models.Count("storeaccount", distinct=True),
            avg_rating=models.Avg("review__score"),
            review_count=models.Count("review", distinct=True),
        )
        .order_by("id")
    )

    if area_name:
        store_qs = store_qs.filter(area__area_name__icontains=area_name)

    if keyword:
        store_qs = store_qs.filter(
            Q(store_name__icontains=keyword) |
            Q(genre__icontains=keyword) |
            Q(address__icontains=keyword)
        )

    # ---------- 時間検索（日跨ぎ対応） ----------
    if search_time_str:
        try:
            search_time = datetime.strptime(search_time_str, "%H:%M").time()

            q1_normal = (
                Q(open_time_1__isnull=False, close_time_1__isnull=False) &
                Q(open_time_1__lte=F("close_time_1")) &
                Q(open_time_1__lte=search_time) &
                Q(close_time_1__gte=search_time)
            )
            q1_cross = (
                Q(open_time_1__isnull=False, close_time_1__isnull=False) &
                Q(open_time_1__gt=F("close_time_1")) &
                (Q(open_time_1__lte=search_time) | Q(close_time_1__gte=search_time))
            )

            q2_normal = (
                Q(open_time_2__isnull=False, close_time_2__isnull=False) &
                Q(open_time_2__lte=F("close_time_2")) &
                Q(open_time_2__lte=search_time) &
                Q(close_time_2__gte=search_time)
            )
            q2_cross = (
                Q(open_time_2__isnull=False, close_time_2__isnull=False) &
                Q(open_time_2__gt=F("close_time_2")) &
                (Q(open_time_2__lte=search_time) | Q(close_time_2__gte=search_time))
            )

            store_qs = store_qs.filter(q1_normal | q1_cross | q2_normal | q2_cross)
        except ValueError:
            pass

    # ---------- ページネーション ----------
    paginator = Paginator(store_qs, 5)
    page_number = request.GET.get("page")
    stores = paginator.get_page(page_number)

    store_ids = [s.id for s in stores]

    # ---------- サムネ ----------
    thumbs = (
        StoreImage.objects
        .filter(store_id__in=store_ids)
        .exclude(image_file__isnull=True)
        .exclude(image_file="")
        .order_by("store_id", "id")
        .values("store_id", "image_file")
    )
    thumb_map = {}
    for row in thumbs:
        thumb_map.setdefault(row["store_id"], row["image_file"])

    # ---------- 予約受付（12日分） ----------
    open_qs = (
        StoreOnlineReservation.objects
        .filter(
            store_id__in=store_ids,
            date__in=date_list,
            booking_status=True,
        )
        .values_list("store_id", "date")
    )
    open_map: dict[int, set[date]] = {}
    for sid, d in open_qs:
        open_map.setdefault(sid, set()).add(d)

    # ---------- 店舗ごとに付与 ----------
    dow_ja = ["月", "火", "水", "木", "金", "土", "日"]

    for s in stores:
        s.thumb_path = thumb_map.get(s.id)

        # annotate の has_account は数値 → bool化
        s.has_account = bool(getattr(s, "has_account", 0) > 0)

        # ---- 星（0.5刻みに切り捨て → 2.5〜2.9 は 2.5） ----
        rating = float(s.avg_rating or 0.0)
        if rating < 0:
            rating = 0.0
        if rating > 5:
            rating = 5.0

        rounded = (int(rating * 2)) / 2.0   # ★0.5刻みで切り捨て

        full = int(rounded)
        half = 1 if (rounded - full) >= 0.5 else 0
        empty = 5 - full - half
        if empty < 0:
            empty = 0

        s.star_states = (["full"] * full) + (["half"] * half) + (["empty"] * empty)

        # 表示用（テンプレの数値表示に使うなら）
        s.display_rating = rounded

        # ---- 12日分カレンダー（紐づき店舗のみ） ----
        if s.has_account:
            opened = open_map.get(s.id, set())
            s.calendar_12 = [
                {
                    "date": d,
                    "month_day": f"{d.month}/{d.day}",
                    "day": d.day,
                    "dow_ja": dow_ja[d.weekday()],
                    "is_sat": d.weekday() == 5,
                    "is_sun": d.weekday() == 6,
                    "is_open": (d in opened),
                }
                for d in date_list
            ]
        else:
            s.calendar_12 = None

    context = {
        "stores": stores,
        "area": area_name,
        "keyword": keyword,
        "time": search_time_str,   # ★ページング引き継ぎ
        "date": date_str,          # ★ページング引き継ぎ
        "MEDIA_URL": settings.MEDIA_URL,
        "base_date": base_date,
    }
    return render(request, "search/customer_search_list.html", context)
