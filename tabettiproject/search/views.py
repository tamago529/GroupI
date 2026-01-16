# search/views.py
from django.views.generic.base import TemplateView

class customer_topView(TemplateView):
    # トップページのテンプレート指定
    template_name = "search/customer_top.html"

class customer_genre_listView(TemplateView):
    # ジャンル一覧のテンプレート指定
    template_name = "search/customer_genre_list.html"

    # テンプレートに変数を渡すための標準的なメソッド
    def get_context_data(self, **kwargs):
        # 親クラスから初期のコンテキストを取得
        context = super().get_context_data(**kwargs)
        
        # テンプレートで使用するデータ構造を定義（main_categories という名前で渡す）
        context['main_categories'] = [
            {
                'name': '和食',
                'children': [
                    {'name': '日本料理', 'image_url': 'image/nihon_ryori.jpg'},
                    {'name': '寿司', 'image_url': 'image/hero.png'},
                    {'name': '海鮮', 'image_url': 'image/kaisen.jpg'},
                    {'name': 'うなぎ・あなご', 'image_url': 'image/unagi.jpg'},
                    {'name': '天ぷら', 'image_url': 'image/tempura.jpg'},
                    {'name': 'とんかつ・揚げ物', 'image_url': 'image/tonkatsu.jpg'},
                ]
            },
            {
                'name': '洋食・西洋料理',
                'children': [
                    {'name': '洋食', 'image_url': 'image/yoshoku.jpg'},
                    {'name': 'ステーキ・鉄板焼', 'image_url': 'image/steak.jpg'},
                    {'name': 'フレンチ', 'image_url': 'image/french.jpg'},
                    {'name': 'イタリアン', 'image_url': 'image/italian.jpg'},
                ]
            },
            {
                'name': '中華料理',
                'children': [
                    {'name': '中華料理', 'image_url': 'image/chuuka.jpg'},
                    {'name': '四川料理', 'image_url': 'image/shisen.jpg'},
                    {'name': '飲茶・点心', 'image_url': 'image/yamucha.jpg'},
                    {'name': '餃子', 'image_url': 'image/gyoza.jpg'},
                ]
            },
            {
                'name': 'カレー',
                'children': [
                    {'name': 'カレー', 'image_url': 'image/curry.jpg'},
                    {'name': 'インドカレー', 'image_url': 'image/india_curry.jpg'},
                    {'name': 'スープカレー', 'image_url': 'image/soup_curry.jpg'},
                ]
            },
            {
                'name': 'ラーメン・つけ麺',
                'children': [
                    {'name': 'ラーメン', 'image_url': 'image/ramen.jpg'},
                    {'name': 'つけ麺', 'image_url': 'image/tsukemen.jpg'},
                    {'name': '担々麺', 'image_url': 'image/tantan.jpg'},
                ]
            }
        ]
        
        # データをセットしたコンテキストを返す
        return context

class customer_search_listView(TemplateView):
    # 検索結果一覧のテンプレート指定
    template_name = "search/customer_search_list.html"