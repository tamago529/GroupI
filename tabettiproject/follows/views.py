from django.views.generic import TemplateView

# ===== フォロー中一覧ビュー =====
class Customer_follow_listView(TemplateView):
    """
    データベースを使わず、変数だけでフォロー一覧を再現する
    """
    template_name = "follows/customer_follow_list.html"

    def get_context_data(self, **kwargs):
        # 親クラスのコンテキストを取得
        context = super().get_context_data(**kwargs)

        # 1. 表示用のタイトルを作成（ログインユーザー名を反映）
        # ログインしていない場合を考慮して名前を固定にするか分岐させる
        if self.request.user.is_authenticated:
            context['profile_title'] = f"{self.request.user.username}のレストランガイド"
        else:
            context['profile_title'] = "ゲストさんのレストランガイド"

        # 2. ダミーのフォローデータ（HTMLの構造に合わせる）
        follow_data = [
            {'user': {'username': 'レオ41919'}, 'review_count': 10, 'follower_count': 4},
            {'user': {'username': '75adf5'}, 'review_count': 1, 'follower_count': 3},
            {'user': {'username': 'ニックネーム16191'}, 'review_count': 11, 'follower_count': 4},
            {'user': {'username': 'グルメ太郎'}, 'review_count': 25, 'follower_count': 10},
        ]

        # 3. コンテキストを渡す
        context['follows'] = follow_data
        context['follow_count'] = len(follow_data)
        context['follow_count'] = len(context['follows'])

        return context


# ===== フォロワー一覧ビュー =====
class Customer_follower_listView(TemplateView):
    """
    データベースを使わず、変数だけでフォロワー一覧を再現する
    """
    template_name = "follows/customer_follower_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # タイトルの作成
        context['profile_title'] = f"{self.request.user.username}のレストランガイド"

        # ダミーのフォロワーデータ
        follower_data = [
            {'user': {'username': 'フォロワーA'}, 'review_count': 5, 'follower_count': 2},
            {'user': {'username': 'フォロワーB'}, 'review_count': 0, 'follower_count': 1},
        ]

        context['follows'] = follower_data
        context['follow_count'] = len(follower_data)

        return context