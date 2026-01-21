from django.shortcuts import render
from django.core.paginator import Paginator
from commons.models import Store

def genre_list(request):
    genres = [
        "焼肉",
        "寿司",
        "ラーメン",
        "居酒屋",
        "カフェ",
        "イタリアン",
        "中華",
        "フレンチ",
    ]
    return render(request, "search/customer_genre_list.html", {
        "genres": genres
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
