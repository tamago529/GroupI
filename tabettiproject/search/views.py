# search/views.py
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

# ============================================================
# ★追加：ID209〜390は「店舗アカウント無しでも」ネット予約を有効化
# （今後範囲が増えるならここだけ触ればOK）
# ============================================================
AUTO_RESERVATION_STORE_ID_MIN = 209
AUTO_RESERVATION_STORE_ID_MAX = 390


def _is_auto_reservation_store_id(store_id: int) -> bool:
    try:
        sid = int(store_id or 0)
    except Exception:
        sid = 0
    return AUTO_RESERVATION_STORE_ID_MIN <= sid <= AUTO_RESERVATION_STORE_ID_MAX


def _default_available_seats(store: Store) -> int:
    seats = int(getattr(store, "seats", 0) or 0)
    return seats if seats > 0 else 999


def _ensure_online_settings_for_12days(stores_page, date_list: list[date]) -> int:
    """
    検索一覧で表示する12日分について、
    ID209-390 の店は StoreOnlineReservation が無ければ自動で作る（○扱いにする）
    戻り値: 作成件数
    """
    # 対象storeを抽出（ページ内のみ）
    targets = []
    for s in stores_page:
        if _is_auto_reservation_store_id(getattr(s, "id", 0)):
            targets.append(s)

    if not targets or not date_list:
        return 0

    store_ids = [s.id for s in targets]
    start = date_list[0]
    end = date_list[-1]

    # 既存を取得（該当範囲）
    existing_pairs = set(
        StoreOnlineReservation.objects.filter(
            store_id__in=store_ids,
            date__range=(start, end),
        ).values_list("store_id", "date")
    )

    to_create = []
    for s in targets:
        for d in date_list:
            if (s.id, d) in existing_pairs:
                continue
            to_create.append(
                StoreOnlineReservation(
                    store=s,
                    date=d,
                    booking_status=True,
                    available_seats=_default_available_seats(s),
                )
            )

    if not to_create:
        return 0

    # UniqueConstraint( store, date ) がある前提なので ignore_conflicts=True で安全に
    StoreOnlineReservation.objects.bulk_create(to_create, ignore_conflicts=True)
    return len(to_create)


# =====================================================
# ジャンル一覧（画像つき）
# =====================================================
def genre_list(request):
    genre_image_map = {
        "日本料理・懐石": "japanese_kaiseki.jpg",
        "寿司・海鮮": "sushi.jpg",
        "うなぎ・肉料理(和)": "unagi.jpg",
        "天ぷら・揚げ物": "tempura.jpg",
        "焼き鳥・鳥料理": "yakitori.jpg",
        "そば・うどん・麺": "noodles.jpg",
        "丼・お好み焼き・おでん": "don_okonomi.jpg",

        "イタリアン・フレンチ": "italian_french.jpg",
        "洋食・ステーキ": "steak.jpg",
        "各国料理(欧米)": "world_food.jpg",

        "中華料理": "chinese.jpg",
        "韓国料理": "korean.jpg",
        "アジア・エスニック": "ethnic.jpg",

        "カレー": "curry.jpg",
        "焼肉・ホルモン": "yakiniku.jpg",
        "鍋料理": "nabe.jpg",

        "ラーメン・麺専門店": "ramen.jpg",

        "居酒屋・ダイニングバー": "izakaya.jpg",
        "バー・パブ": "bar.jpg",
        "ビアガーデン・ホール": "beer.jpg",

        "カフェ・喫茶店": "cafe.jpg",
        "パン・サンドイッチ": "bread.jpg",
        "スイーツ・和菓子": "sweets.jpg",

        "レストラン・食堂": "restaurant.jpg",
        "その他施設": "other.jpg",
    }

    def _item(name: str, tags: str) -> dict:
        return {
            "name": name,
            "tags": tags,
            "image": genre_image_map.get(name, "noimage.jpg"),
        }

    genre_data = [
        {
            "category": "和食",
            "items": [
                _item("日本料理・懐石", "日本料理｜郷土料理｜豆腐料理｜料理旅館"),
                _item("寿司・海鮮", "寿司｜回転寿司｜海鮮｜ふぐ｜かに｜えび｜貝"),
                _item("うなぎ・肉料理(和)", "うなぎ｜あなご｜すき焼き｜しゃぶしゃぶ｜牛タン"),
                _item("天ぷら・揚げ物", "天ぷら｜とんかつ｜串揚げ｜からあげ"),
                _item("焼き鳥・鳥料理", "焼き鳥｜串焼き｜もつ焼き｜手羽先"),
                _item("そば・うどん・麺", "そば｜うどん｜ほうとう｜ちゃんぽん｜焼きそば"),
                _item("丼・お好み焼き・おでん", "牛丼｜親子丼｜天丼｜かつ丼｜海鮮丼｜お好み焼き｜もんじゃ｜たこ焼き｜おでん"),
            ],
        },
        {
            "category": "洋食・西洋料理",
            "items": [
                _item("イタリアン・フレンチ", "イタリアン｜パスタ｜ピザ｜フレンチ｜ビストロ"),
                _item("洋食・ステーキ", "洋食｜ハンバーグ｜オムライス｜ステーキ｜鉄板焼"),
                _item("各国料理(欧米)", "スペイン料理｜ドイツ料理｜ロシア料理｜アメリカ料理｜ハンバーガー"),
            ],
        },
        {
            "category": "中華・アジア・エスニック",
            "items": [
                _item("中華料理", "中華料理｜四川料理｜広東料理｜上海料理｜飲茶｜点心｜餃子"),
                _item("韓国料理", "韓国料理｜サムギョプサル｜冷麺"),
                _item("アジア・エスニック", "タイ料理｜ベトナム料理｜インドネシア料理｜インド料理｜中東料理｜メキシコ料理"),
            ],
        },
        {
            "category": "カレー・焼肉・鍋",
            "items": [
                _item("カレー", "カレー｜インドカレー｜スープカレー｜欧風カレー"),
                _item("焼肉・ホルモン", "焼肉｜ホルモン｜ジンギスカン｜バーベキュー"),
                _item("鍋料理", "もつ鍋｜水炊き｜ちゃんこ鍋｜火鍋｜うどんすき"),
            ],
        },
        {
            "category": "ラーメン・つけ麺",
            "items": [
                _item("ラーメン・麺専門店", "ラーメン｜つけ麺｜まぜそば｜担々麺｜刀削麺"),
            ],
        },
        {
            "category": "居酒屋・バー・お酒",
            "items": [
                _item("居酒屋・ダイニングバー", "居酒屋｜立ち飲み｜バル｜肉バル｜ダイニングバー"),
                _item("バー・パブ", "バー｜ワインバー｜ビアバー｜スポーツバー｜日本酒バー"),
                _item("ビアガーデン・ホール", "ビアガーデン｜ビアホール"),
            ],
        },
        {
            "category": "カフェ・パン・スイーツ",
            "items": [
                _item("カフェ・喫茶店", "カフェ｜喫茶店｜コーヒースタンド｜ティーパレス"),
                _item("パン・サンドイッチ", "パン｜サンドイッチ｜ベーカリー"),
                _item("スイーツ・和菓子", "ケーキ｜パフェ｜和菓子｜大福｜かき氷｜アイスクリーム"),
            ],
        },
        {
            "category": "その他・施設",
            "items": [
                _item("レストラン・食堂", "ファミレス｜食堂｜弁当｜惣菜｜オーガニック｜ビュッフェ"),
                _item("その他施設", "カラオケ｜ホテル｜道の駅｜コンビニ｜屋形船"),
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

    # 利用シーン
    scene_id_str = (request.GET.get("scene") or "").strip()

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
            weighted_avg_rating=models.Sum(
                models.F("review__score") * models.F("review__reviewer__trust_score")
            ) / models.Sum(models.F("review__reviewer__trust_score")),
            avg_rating=models.Avg("review__score"),
            review_count=models.Count("review", distinct=True),
        )
    )

    # ---------- ソート順 ----------
    sort_key = request.GET.get("sort")
    if sort_key == "rating":
        store_qs = store_qs.order_by("-weighted_avg_rating", "id")
    elif sort_key == "reviews":
        store_qs = store_qs.order_by("-review_count", "id")
    else:
        store_qs = store_qs.order_by("id")

    # ---------- 絞り込み ----------
    if area_name:
        store_qs = store_qs.filter(area__area_name__icontains=area_name)

    if keyword:
        store_qs = store_qs.filter(
            Q(store_name__icontains=keyword) |
            Q(genre__icontains=keyword) |
            Q(genre_master__name__icontains=keyword) |
            Q(address__icontains=keyword)
        )

    if scene_id_str:
        try:
            scene_id = int(scene_id_str)
            store_qs = store_qs.filter(scene_id=scene_id)
        except ValueError:
            pass

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

    # =========================================================
    # ★ここが追加の本体
    # ID209-390の店は、12日分の予約設定が無ければ自動生成して「○」扱いにする
    # =========================================================
    created_count = _ensure_online_settings_for_12days(stores, date_list)
    # 必要ならデバッグ（本番では消してOK）
    # print(f"DEBUG: auto online settings created={created_count}")

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

        real_has_account = bool(getattr(s, "has_account", 0) > 0)
        is_auto = _is_auto_reservation_store_id(s.id)

        # ★テンプレ表示判定：店アカウント or 自動予約対象
        s.has_account = real_has_account or is_auto

        rating = float(s.weighted_avg_rating or s.avg_rating or 0.0)
        if rating < 0:
            rating = 0.0
        if rating > 5:
            rating = 5.0

        rounded = (int(rating * 2)) / 2.0
        full = int(rounded)
        half = 1 if (rounded - full) >= 0.5 else 0
        empty = 5 - full - half
        if empty < 0:
            empty = 0

        s.star_states = (["full"] * full) + (["half"] * half) + (["empty"] * empty)
        s.display_rating = rating

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

    page_range = paginator.get_elided_page_range(
        number=stores.number,
        on_each_side=3,
        on_ends=2
    )

    context = {
        "stores": stores,
        "page_range": page_range,
        "area": area_name,
        "keyword": keyword,
        "scene": scene_id_str,
        "sort": sort_key,
        "time": search_time_str,
        "date": date_str,
        "MEDIA_URL": settings.MEDIA_URL,
        "base_date": base_date,
    }
    return render(request, "search/customer_search_list.html", context)


# =====================================================
# ユーザー検索
# =====================================================
def customer_user_search_listView(request):
    from commons.models import CustomerAccount, Follow

    keyword = (request.GET.get("keyword") or "").strip()

    user_qs = CustomerAccount.objects.all()
    if keyword:
        user_qs = user_qs.filter(
            Q(nickname__icontains=keyword) |
            Q(username__icontains=keyword)
        )

    paginator = Paginator(user_qs.order_by("id"), 20)
    page_number = request.GET.get("page")
    users_page = paginator.get_page(page_number)

    login_customer = None
    if request.user.is_authenticated:
        login_customer = CustomerAccount.objects.filter(pk=request.user.pk).first()

    user_list = []
    for target in users_page:
        if login_customer and target.pk == login_customer.pk:
            continue

        follower_count = Follow.objects.filter(followee=target).count()
        is_following = False
        is_follower = False
        is_muted = False

        if login_customer:
            rel = Follow.objects.filter(follower=login_customer, followee=target).first()
            is_following = rel is not None
            if rel:
                is_muted = rel.is_muted

            is_follower = Follow.objects.filter(follower=target, followee=login_customer).exists()

        cover_field = getattr(target, "cover_image", None)
        icon_field = getattr(target, "icon_image", None)

        user_list.append({
            "id": target.pk,
            "user": target,
            "review_count": target.review_count,
            "follower_count": follower_count,
            "is_following": is_following,
            "is_follower": is_follower,
            "is_muted": is_muted,
            "cover_image_url": cover_field.url if cover_field else "",
            "user_icon_url": icon_field.url if icon_field else "",
        })

    page_range = paginator.get_elided_page_range(
        number=users_page.number,
        on_each_side=3,
        on_ends=2
    )

    context = {
        "users": users_page,
        "user_list": user_list,
        "keyword": keyword,
        "page_range": page_range,
    }
    return render(request, "search/user_search_list.html", context)
