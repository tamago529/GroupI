from django.shortcuts import render
from django.core.paginator import Paginator
from commons.models import Store

def genre_list(request):
    # 構造化されたデータ（大分類名：{画像, 小分類リスト}）
    genre_data = [
        {
            "category": "和食",
            "items": [
                {"name": "日本料理", "images":"#"},
                {"name": "寿司", "image": "sushi.jpg", "tags": "寿司 | 回転寿司 | 立ち食い寿司｜いなり寿司｜棒寿司"},
                {"name": "海鮮", "images":"#", "tags": "海鮮｜ふぐ｜かに｜すっぽん｜あんこう｜かき"},
                {"name": "うなぎ・あなご", "images":"#", "tags": "うなぎ｜あなご｜どじょう"},
                {"name": "天ぷら", "images":"#"},
                {"name": "とんかつ・揚げ物", "images":"#", "tags": "とんかつ｜牛カツ｜串揚げ｜からあげ｜揚げ物"},
                {"name": "焼き鳥・串焼・鳥料理", "images":"#", "tags": "焼き鳥｜串焼き｜もつ焼き｜鳥料理｜手羽先"},
                {"name": "すき焼き", "images":"#"},
                {"name": "しゃぶしゃぶ", "images":"#", "tags": "しゃぶしゃぶ｜豚しゃぶ"},
                {"name": "そば", "images":"#", "tags": "そば｜立ち食いそば"},
                {"name": "うどん", "images":"#", "tags": "うどん｜カレーうどん"},
                {"name": "麺類", "images":"#", "tags": "麺類｜焼きそば｜沖縄そば｜ほうとう｜ちゃんぽん"},
                {"name": "お好み焼き・たこ焼き", "images":"#", "tags": "お好み焼き｜もんじゃ焼き｜たこ焼き｜明石焼き"},
                {"name": "丼", "images":"#", "tags": "丼｜牛丼｜親子丼｜天丼｜かつ丼｜海鮮丼｜豚丼"},
                {"name": "おでん", "images":"#"},
                {"name": "その他", "images":"#", "tags": "郷土料理｜沖縄料理｜牛タン｜麦とろ｜釜飯｜お茶漬け｜豆腐料理｜ろばた焼き｜きりたんぽ｜くじら料理"},
            ]
        },
        {
            "category": "洋食・西洋料理",
            "items": [
                {"name": "洋食", "image": "#", "tags": "洋食｜ハンバーグ｜オムライス｜コロッケ｜スープ"},
                {"name": "ステーキ・鉄板焼", "image": "#", "tags": "ステーキ｜鉄板焼"},
                {"name": "フレンチ", "image": "french.jpg", "tags": "ビストロ | フレンチ"},
                {"name": "イタリアン", "image": "italian.jpg", "tags": "パスタ | ピザ"},
                {"name": "スペイン料理", "image": "#"},
                {"name": "ヨーロッパ料理", "image": "#", "tags": "ヨーロッパ料理｜ポルトガル料理｜ドイツ料理｜ロシア料理｜ギリシャ料理"},
                {"name": "アメリカ料理", "image": "#", "tags": "アメリカ料理｜カリフォルニア料理｜ハワイ料理｜ハンバーガー｜ホットドック"},
            ]
        },
        {
            "category": "中華料理",
            "items": [
                {"name": "中華料理", "image": "#"},
                {"name": "四川料理", "image": "#"},
                {"name": "台湾料理", "image": "#"},
                {"name": "飯茶・点心", "image": "#"},
                {"name": "餃子", "image": "#"},
                {"name": "肉まん", "image": "#"},
                {"name": "小籠包", "image": "#"},
                {"name": "中華粥", "image": "#"},
            ]
        },
        {
            "category": "アジア・エスニック",
            "items": [
                {"name": "アジア・エスニック", "image": "#"},
                {"name": "韓国料理", "image": "#", "tags": "韓国料理｜冷麺"},
                {"name": "東南アジア料理", "image": "#", "tags": "東南アジア料理｜タイ料理｜ベトナム料理｜バインミー｜インドネシア料理｜シンガポール料理"},
                {"name": "南アジア料理", "image": "#", "tags": "南アジア料理｜インド料理｜ネパール料理｜パキスタン料理｜スリランカ料理"},
                {"name": "中東料理", "image": "#", "tags": "中東料理｜トルコ料理｜ケバブ｜モロッコ料理｜ファラフェル"},
                {"name": "中南米料理", "image": "#", "tags": "中南米料理｜メキシコ料理｜タコス｜ブラジル料理｜ペルー料理"},
                {"name": "アフリカ料理", "image": "#"},
            ]
        },
        {
            "category": "カレー",
            "items": [
                {"name": "カレー", "image": "#"},
                {"name": "インドカレー", "image": "#"},
                {"name": "スープカレー", "image": "#"},
            ]
        },
        {
            "category": "焼肉・ホルモン",
            "items": [
                {"name": "焼肉", "image": "#"},
                {"name": "ホルモン", "image": "#"},
                {"name": "ジンギスカン", "image": "#"},
            ]
        },
        {
            "category": "鍋",
            "items": [
                {"name": "鍋", "image": "#"},
                {"name": "もつ鍋", "image": "#"},
                {"name": "水吹き", "image": "#"},
                {"name": "ちゃんこ鍋", "image": "#"},
                {"name": "火鍋", "image": "#"},
                {"name": "うどんすき", "image": "#"},
            ]
        },
        {
            "category": "居酒屋",
            "items": [
                {"name": "居酒屋", "image": "#"},
                {"name": "ダイニングバー", "image": "#"},
                {"name": "立ち飲み", "image": "#"},
                {"name": "バル", "image": "#", "tags": "バル｜肉バル"},
                {"name": "ビアガーデン・ビアホール", "image": "#", "tags": "ビアガーデン｜ビアホール"},
            ]
        },
        {
            "category": "その他レストラン",
            "items": [
                {"name": "レストラン・食堂", "image": "#", "tags": "レストラン｜ファミレス｜食堂｜学生食堂｜社員食堂"},
                {"name": "創作料理・イノベーティブ", "image": "#", "tags": "創作料理｜イノベーティブ"},
                {"name": "オーガニック・薬膳", "image": "#", "tags": "オーガニック｜薬膳"},
                {"name": "弁当・おにぎり・惣菜", "image": "#", "tags": "弁当｜おにぎり｜惣菜・デリ"},
                {"name": "肉料理", "image": "#", "tags": "肉料理｜牛料理｜豚料理｜馬肉料理｜ジビエ料理"},
                {"name": "シーフード", "image": "#", "tags": "シーフード｜オイスターバー"},
                {"name": "サラダ・野菜料理", "image": "#", "tags": "サラダ｜野菜料理"},
                {"name": "チーズ料理", "image": "#"},
                {"name": "にんにく料理", "image": "#"},
                {"name": "ビュッフェ", "image": "#"},
                {"name": "バーベキュー", "image": "#"},
                {"name": "屋形船・クルージング", "image": "#"},
            ]
        },
        {
            "category": "ラーメン・つけ麺",
            "items": [
                {"name": "ラーメン", "image": "#",},
                {"name": "つけ麺", "image": "#"},
                {"name": "油そば・まぜそば", "image": "#"},
                {"name": "台湾まぜそば", "image": "#"},
                {"name": "担々麺", "image": "#"},
                {"name": "汁なし担々麵", "image": "#"},
                {"name": "刀削麺", "image": "#"},
            ]
        },
        {
            "category": "カフェ・喫茶店",
            "items": [
                {"name": "カフェ", "image": "#"},
                {"name": "喫茶店", "image": "#"},
                {"name": "甘味処", "image": "#"},
                {"name": "フルーツパーラー", "image": "#"},
                {"name": "パンケーキ", "image": "#"},
                {"name": "コーヒースタンド", "image": "#"},
                {"name": "ティースタンド", "image": "#"},
                {"name": "ジューススタンド", "image": "#"},
                {"name": "タピオカ", "image": "#"},
            ]
        },
        {
            "category": "スイーツ",
            "items": [
                {"name": "スイーツ", "image": "#"},
                {"name": "洋菓子", "image": "#"},
                {"name": "ケーキ", "image": "#"},
                {"name": "シュークリーム", "image": "#"},
                {"name": "チョコレート", "image": "#"},
                {"name": "ドーナツ", "image": "#"},
                {"name": "マカロン", "image": "#"},
                {"name": "バームクーヘン", "image": "#"},
                {"name": "プリン", "image": "#"},
                {"name": "グレープ・ガレット", "image": "#"},
                {"name": "和菓子", "image": "#"},
                {"name": "大福", "image": "#"},
                {"name": "たい焼き・大判焼き", "image": "#"},
                {"name": "どら焼き", "image": "#"},
                {"name": "カステラ", "image": "#"},
                {"name": "焼き芋・大学芋", "image": "#"},
                {"name": "せんべい", "image": "#"},
                {"name": "中華菓子", "images": "#"},
                {"name": "ジェラート・アイスクリーム", "images": "#"},
                {"name": "ソフトクリーム", "images": "#"},
                {"name": "かき氷", "images": "#"},
            ]
        },
        {
            "category": "パン・サンドイッチ",
            "items": [
                {"name": "パン", "image": "#"},
                {"name": "パブ", "image": "#"},
                {"name": "ワインバー", "image": "#"},
                {"name": "ビアバー", "image": "#"},
                {"name": "スポーツバー", "image": "#"},
                {"name": "日本酒バー", "image": "#"},
                {"name": "焼酎バー", "images": "#"},
            ]
        },
        {
            "category": "料理旅館・オーベルジュ",
            "items": [
                {"name": "料理旅館", "image": "#"},
                {"name": "オーベルジュ", "image": "#"},
            ]
        },
        {
            "category": "その他",
            "items": [
                {"name": "その他", "image": "#", "tags": "その他｜カラオケ｜ダーツ｜ホテル｜旅館・民宿｜結婚式場｜道の駅｜コンビニ・スーパー｜売店"},
            ]
        },
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
