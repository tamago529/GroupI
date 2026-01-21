from django.views.generic import TemplateView
from django.shortcuts import render

def get_default_follows():
    """フォロー中の初期データ"""
    return [
        {'id': 1, 'user': {'username': 'レオ41919'}, 'review_count': 10, 'follower_count': 4},
        {'id': 2, 'user': {'username': '75adf5'}, 'review_count': 1, 'follower_count': 3},
        {'id': 3, 'user': {'username': 'ニックネーム16191'}, 'review_count': 11, 'follower_count': 4},
        {'id': 4, 'user': {'username': 'グルメ太郎'}, 'review_count': 25, 'follower_count': 10},
    ]

def get_default_followers():
    """フォロワーの初期データ"""
    return [
        {'id': 101, 'user': {'username': 'フォロワーA'}, 'review_count': 5, 'follower_count': 2, 'is_following': False},
        {'id': 102, 'user': {'username': 'フォロワーB'}, 'review_count': 0, 'follower_count': 1, 'is_following': False},
    ]

class Customer_follower_listView(TemplateView):
    template_name = "follows/customer_follower_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile_title'] = f"{self.request.user.username}のレストランガイド"

        if 'my_followers' not in self.request.session:
            self.request.session['my_followers'] = get_default_followers()
        
        context['followers'] = self.request.session['my_followers']
        context['follower_count'] = len(context['followers'])
        return context

    def post(self, request, *args, **kwargs):
        user_id_to_toggle = request.POST.get('user_id')
        
        # 各セッションデータの取得
        followers = request.session.get('my_followers', get_default_followers())
        follows = request.session.get('my_follows', get_default_follows())

        for item in followers:
            if str(item['id']) == user_id_to_toggle:
                if not item['is_following']:
                    # 1. フォローを追加する場合
                    item['is_following'] = True
                    # フォロー中リストに重複がないか確認して追加
                    if not any(f['id'] == item['id'] for f in follows):
                        follows.append({
                            'id': item['id'],
                            'user': item['user'],
                            'review_count': item['review_count'],
                            'follower_count': item['follower_count']
                        })
                else:
                    # 2. フォローを解除する場合
                    item['is_following'] = False
                    # フォロー中リストから削除
                    follows = [f for f in follows if str(f['id']) != user_id_to_toggle]
                break

        # セッションを更新
        request.session['my_followers'] = followers
        request.session['my_follows'] = follows
        request.session.modified = True 

        return render(request, self.template_name, {
            'profile_title': f"{request.user.username}のレストランガイド",
            'followers': followers,
            'follower_count': len(followers),
        })

class Customer_follow_listView(TemplateView):
    template_name = "follows/customer_follow_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile_title'] = f"{self.request.user.username}のレストランガイド"
        
        if 'my_follows' not in self.request.session:
            self.request.session['my_follows'] = get_default_follows()

        context['follows'] = self.request.session['my_follows']
        context['follow_count'] = len(context['follows'])
        return context

    def post(self, request, *args, **kwargs):
        user_id_to_remove = request.POST.get('user_id')
        follows = request.session.get('my_follows', get_default_follows())
        
        # 解除処理
        updated_follows = [f for f in follows if str(f['id']) != user_id_to_remove]
        request.session['my_follows'] = updated_follows
        
        # フォロワーリスト側も同期（もしフォロワーA/Bならボタンを未フォローに戻す）
        followers = request.session.get('my_followers', get_default_followers())
        for f in followers:
            if str(f['id']) == user_id_to_remove:
                f['is_following'] = False
        
        request.session['my_followers'] = followers
        request.session.modified = True

        return render(request, self.template_name, {
            'profile_title': f"{request.user.username}のレストランガイド",
            'follows': updated_follows,
            'follow_count': len(updated_follows),
        })