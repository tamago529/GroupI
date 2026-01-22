from django.shortcuts import render
from django.core.paginator import Paginator
from commons.models import Store

def genre_list(request):
    # 構造化されたデータ（大分類名：{画像, 小分類リスト}）
    genre_data =[
            {
                "category": "和食",
                "items": [
                    {"name": "日本料理・懐石", "tags": "日本料理｜郷土料理｜豆腐料理｜料理旅館"},
                    {"name": "寿司・海鮮", "tags": "寿司｜回転寿司｜海鮮｜ふぐ｜かに｜えび｜貝"},
                    {"name": "うなぎ・肉料理(和)", "tags": "うなぎ｜あなご｜すき焼き｜しゃぶしゃぶ｜牛タン"},
                    {"name": "天ぷら・揚げ物", "tags": "天ぷら｜とんかつ｜串揚げ｜からあげ"},
                    {"name": "焼き鳥・鳥料理", "tags": "焼き鳥｜串焼き｜もつ焼き｜手羽先"},
                    {"name": "そば・うどん・麺", "tags": "そば｜うどん｜ほうとう｜ちゃんぽん｜焼きそば"},
                    {"name": "丼・お好み焼き・おでん", "tags": "牛丼｜親子丼｜天丼｜かつ丼｜海鮮丼｜お好み焼き｜もんじゃ｜たこ焼き｜おでん"}
                ]
            },
            {
                "category": "洋食・西洋料理",
                "items": [
                    {"name": "イタリアン・フレンチ", "tags": "イタリアン｜パスタ｜ピザ｜フレンチ｜ビストロ"},
                    {"name": "洋食・ステーキ", "tags": "洋食｜ハンバーグ｜オムライス｜ステーキ｜鉄板焼"},
                    {"name": "各国料理(欧米)", "tags": "スペイン料理｜ドイツ料理｜ロシア料理｜アメリカ料理｜ハンバーガー"}
                ]
            },
            {
                "category": "中華・アジア・エスニック",
                "items": [
                    {"name": "中華料理", "tags": "中華料理｜四川料理｜広東料理｜上海料理｜飲茶｜点心｜餃子"},
                    {"name": "韓国料理", "tags": "韓国料理｜サムギョプサル｜冷麺"},
                    {"name": "アジア・エスニック", "tags": "タイ料理｜ベトナム料理｜インドネシア料理｜インド料理｜中東料理｜メキシコ料理"}
                ]
            },
            {
                "category": "カレー・焼肉・鍋",
                "items": [
                    {"name": "カレー", "tags": "カレー｜インドカレー｜スープカレー｜欧風カレー"},
                    {"name": "焼肉・ホルモン", "tags": "焼肉｜ホルモン｜ジンギスカン｜バーベキュー"},
                    {"name": "鍋料理", "tags": "もつ鍋｜水炊き｜ちゃんこ鍋｜火鍋｜うどんすき"}
                ]
            },
            {
                "category": "ラーメン・つけ麺",
                "items": [
                    {"name": "ラーメン・麺専門店", "tags": "ラーメン｜つけ麺｜まぜそば｜担々麺｜刀削麺"}
                ]
            },
            {
                "category": "居酒屋・バー・お酒",
                "items": [
                    {"name": "居酒屋・ダイニングバー", "tags": "居酒屋｜立ち飲み｜バル｜肉バル｜ダイニングバー"},
                    {"name": "バー・パブ", "tags": "バー｜ワインバー｜ビアバー｜スポーツバー｜日本酒バー"},
                    {"name": "ビアガーデン・ホール", "tags": "ビアガーデン｜ビアホール"}
                ]
            },
            {
                "category": "カフェ・パン・スイーツ",
                "items": [
                    {"name": "カフェ・喫茶店", "tags": "カフェ｜喫茶店｜コーヒースタンド｜ティーパレス"},
                    {"name": "パン・サンドイッチ", "tags": "パン｜サンドイッチ｜ベーカリー"},
                    {"name": "スイーツ・和菓子", "tags": "ケーキ｜パフェ｜和菓子｜大福｜かき氷｜アイスクリーム"}
                ]
            },
            {
                "category": "その他・施設",
                "items": [
                    {"name": "レストラン・食堂", "tags": "ファミレス｜食堂｜弁当｜惣菜｜オーガニック｜ビュッフェ"},
                    {"name": "その他施設", "tags": "カラオケ｜ホテル｜道の駅｜コンビニ｜屋形船"}
                ]
            }
        ]
    
    return render(request, "search/customer_genre_list.html", {
        "genre_data": genre_data
    })

def customer_search_listView(request):
    store_qs = Store.objects.select_related("area", "scene").order_by("id")

    area_name = request.GET.get("area")
    keyword = request.GET.get("keyword")

    if area_name:
        store_qs = store_qs.filter(area__area_name__icontains=area_name)

    if keyword:
        store_qs = store_qs.filter(store_name__icontains=keyword)

    paginator = Paginator(store_qs, 5)
    page_number = request.GET.get("page")
    stores = paginator.get_page(page_number)

    context = {
        "stores": stores,
        "area": area_name,        # ⭐ 追加
        "keyword": keyword,       # ⭐ 追加
    }
    return render(request, "search/customer_search_list.html", context)
