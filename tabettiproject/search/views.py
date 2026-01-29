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
# ジャンル一覧（画像つき）
# =====================================================
from commons.constants import GENRE_STRUCTURE

def genre_list(request):
    # ジャンル名 → 画像ファイル名（static/images/ 配下に置く想定）
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

    genre_data = []
    for group in GENRE_STRUCTURE:
        cat = group["category"]
        items_data = []
        for name, tags in group["items"]:
            items_data.append({
                "name": name,
                "tags": tags,
                "image": genre_image_map.get(name, "noimage.jpg"),
            })
        
        genre_data.append({
            "category": cat,
            "items": items_data,
        })

    return render(request, "search/customer_genre_list.html", {"genre_data": genre_data})


# =====================================================
# 検索結果（店舗一覧）
# =====================================================
def customer_search_listView(request):
    # ---------- 検索条件 ----------
    area_name = (request.GET.get("area") or "").strip()
    keyword = (request.GET.get("keyword") or "").strip()
    search_time_str = (request.GET.get("time") or "").strip()

    # ★追加：利用シーン
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
            # 信頼度による加重平均評価
            weighted_avg_rating=models.Sum(
                models.F("review__score") * models.F("review__reviewer__trust_score")
            ) / models.Sum(models.F("review__reviewer__trust_score")),
            # 通常の平均評価（比較用）
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
            Q(address__icontains=keyword)
        )

    # ★追加：利用シーン（store_qs 定義の「後」に必ず置く）
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

        s.has_account = bool(getattr(s, "has_account", 0) > 0)

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

        # 表示用（テンプレの数値表示に使うなら）
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
    
    # 全顧客アカウントをベースにキーワード検索
    user_qs = CustomerAccount.objects.all()
    if keyword:
        user_qs = user_qs.filter(
            Q(nickname__icontains=keyword) | 
            Q(username__icontains=keyword)
        )
    
    # ページネーション（検索画面と同じ実装）
    paginator = Paginator(user_qs.order_by("id"), 20)
    page_number = request.GET.get("page")
    users_page = paginator.get_page(page_number)

    # ログインユーザー情報の取得
    login_customer = None
    if request.user.is_authenticated:
        login_customer = CustomerAccount.objects.filter(pk=request.user.pk).first()

    # 表示用データの整形（フォロー状態など）
    user_list = []
    for target in users_page:
        # 自分自身は検索結果から除外するか、区別する
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

    # 省略表示用のページ範囲（前後3ページ、端2ページ）
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
