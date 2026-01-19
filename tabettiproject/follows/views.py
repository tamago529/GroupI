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


# follows/views.py の該当部分

class Customer_follower_listView(TemplateView):
    """
    フォロワー一覧を表示するビュー（ダミーデータ版）
    """
    template_name = "follows/customer_follower_list.html"

    def get_context_data(self, **kwargs):
        # 親クラスのコンテキストを取得
        context = super().get_context_data(**kwargs)

        # プロフィールタイトルの設定
        if self.request.user.is_authenticated:
            context['profile_title'] = f"{self.request.user.username}のレストランガイド"
        else:
            context['profile_title'] = "ゲストさんのレストランガイド"

        # フォロワー用のダミーデータ（フォロー中とは別のリストとして作成）
        context['followers'] = [
            {'user': {'username': 'グルメ好き123'}, 'review_count': 5, 'follower_count': 12},
            {'user': {'username': '食べ歩きマスター'}, 'review_count': 42, 'follower_count': 150},
            {'user': {'username': 'ランチ巡り隊'}, 'review_count': 18, 'follower_count': 25},
        ]
        
        # フォロワー数をカウント
        context['follower_count'] = len(context['followers'])

        return context