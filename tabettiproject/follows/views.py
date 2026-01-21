from django.views.generic import TemplateView
from django.shortcuts import render
from commons.models import CustomerAccount 
from django.contrib.auth.mixins import LoginRequiredMixin

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

class Customer_follower_listView(LoginRequiredMixin, TemplateView):
    template_name = "follows/customer_follower_list.html"

    def _get_login_customer(self):
        # ✅ 継承モデル対策：pkで引き直す
        return CustomerAccount.objects.filter(pk=self.request.user.pk).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        customer = self._get_login_customer()
        cover_field = getattr(customer, "cover_image", None) if customer else None
        icon_field = getattr(customer, "icon_image", None) if customer else None

        # タイトル
        display_name = customer.nickname if customer else self.request.user.username
        context["profile_title"] = f"{display_name}のレストランガイド"

        # ✅ 追加：カバー/アイコン/表示名
        context["customer"] = customer
        context["user_name"] = display_name
        context["cover_image_url"] = cover_field.url if cover_field else ""
        context["user_icon_url"] = icon_field.url if icon_field else ""

        if "my_followers" not in self.request.session:
            self.request.session["my_followers"] = get_default_followers()

        context["followers"] = self.request.session["my_followers"]
        context["follower_count"] = len(context["followers"])
        return context

class Customer_follow_listView(LoginRequiredMixin, TemplateView):
    template_name = "follows/customer_follow_list.html"

    def _get_login_customer(self):
        # ✅ 継承モデル対策：pkで引き直す
        return CustomerAccount.objects.filter(pk=self.request.user.pk).first()

    def _build_profile_context(self):
        customer = self._get_login_customer()
        cover_field = getattr(customer, "cover_image", None) if customer else None
        icon_field = getattr(customer, "icon_image", None) if customer else None

        display_name = customer.nickname if customer else self.request.user.username

        return {
            "customer": customer,
            "user_name": display_name,
            "profile_title": f"{display_name}のレストランガイド",
            "cover_image_url": cover_field.url if cover_field else "",
            "user_icon_url": icon_field.url if icon_field else "",
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ✅ プロフィール情報（cover/icon/name）
        context.update(self._build_profile_context())

        # ✅ フォロー中データ
        if "my_follows" not in self.request.session:
            self.request.session["my_follows"] = get_default_follows()

        context["follows"] = self.request.session["my_follows"]
        context["follow_count"] = len(context["follows"])
        return context

    def post(self, request, *args, **kwargs):
        user_id_to_remove = request.POST.get("user_id")
        follows = request.session.get("my_follows", get_default_follows())

        # 解除処理
        updated_follows = [f for f in follows if str(f["id"]) != str(user_id_to_remove)]
        request.session["my_follows"] = updated_follows

        # フォロワーリスト側も同期（もしフォロワーA/Bならボタンを未フォローに戻す）
        followers = request.session.get("my_followers", get_default_followers())
        for f in followers:
            if str(f["id"]) == str(user_id_to_remove):
                f["is_following"] = False

        request.session["my_followers"] = followers
        request.session.modified = True

        # ✅ renderでもプロフィール情報（cover/icon/name）を渡す
        ctx = self._build_profile_context()
        ctx.update({
            "follows": updated_follows,
            "follow_count": len(updated_follows),
        })
        return render(request, self.template_name, ctx)
