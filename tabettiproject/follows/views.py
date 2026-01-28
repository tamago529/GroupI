from django.views.generic import TemplateView
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.db import IntegrityError, transaction

from django.db.models import Sum
from commons.models import CustomerAccount, Follow, Review,ReviewPhoto



def _get_login_customer_or_404(request):
    """
    multi-table継承（Account -> CustomerAccount）対策：
    request.user.pk で CustomerAccount を引き直す
    """
    customer = CustomerAccount.objects.filter(pk=request.user.pk).first()
    if not customer:
        raise Http404("CustomerAccount not found")
    return customer


def _pack_user_card(viewer: CustomerAccount, target: CustomerAccount):
    """
    テンプレの item.user.username 互換を保つため dict で返す
    """
    follower_count = Follow.objects.filter(followee=target).count()

    rel = Follow.objects.filter(follower=viewer, followee=target).only("is_muted").first()
    is_following = rel is not None
    is_muted = rel.is_muted if rel else False

    is_follower = Follow.objects.filter(follower=target, followee=viewer).exists()

    # ✅ 追加：相手ユーザーのカバー/アイコン
    cover_field = getattr(target, "cover_image", None)
    icon_field = getattr(target, "icon_image", None)

    return {
        "id": target.pk,
        "user": target,
        "review_count": target.review_count,
        "follower_count": follower_count,
        "is_following": is_following,
        "is_follower": is_follower,
        "is_muted": is_muted,

        # ✅ 追加（カードで使う）
        "cover_image_url": cover_field.url if cover_field else "",
        "user_icon_url": icon_field.url if icon_field else "",
    }



class Customer_follower_listView(LoginRequiredMixin, TemplateView):
    template_name = "follows/customer_follower_list.html"

    def _get_target_customer(self):
        customer_id = self.kwargs.get("customer_id")
        if customer_id:
            return get_object_or_404(CustomerAccount, pk=customer_id)
        return CustomerAccount.objects.filter(pk=self.request.user.pk).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        customer = self._get_target_customer()
        if not customer:
            raise Http404("CustomerAccount not found")
        
        readonly_mode = (customer.pk != self.request.user.pk)
        viewer = CustomerAccount.objects.filter(pk=self.request.user.pk).first()

        cover_field = getattr(customer, "cover_image", None)
        icon_field = getattr(customer, "icon_image", None)

        display_name = customer.nickname or customer.username
        context["profile_title"] = f"{display_name}のレストランガイド"

        context["customer"] = customer
        context["user_name"] = display_name
        context["cover_image_url"] = cover_field.url if cover_field else ""
        context["user_icon_url"] = icon_field.url if icon_field else ""
        context["readonly_mode"] = readonly_mode

        # ✅ あなたをフォローしている人（フォロワー）
        follower_rels = (
            Follow.objects
            .filter(followee=customer)
            .select_related("follower")
            .order_by("-followed_at")
        )

        followers = [_pack_user_card(viewer or customer, rel.follower) for rel in follower_rels]

        context["followers"] = followers
        context["follower_count"] = len(followers)
        return context

    def post(self, request, *args, **kwargs):
        """
        フォロワー一覧での操作：
        - action=follow       -> Follow作成（adminにも反映）-> フォロー中一覧へ
        - action=unfollow     -> Follow削除（adminからも消える）-> フォロワー一覧へ
        - action=toggle_mute  -> Follow.is_muted をトグル（adminにも反映）-> フォロワー一覧へ

        互換：actionが無い場合は従来通り「存在すれば解除／無ければフォロー」を実行
        """
        customer = CustomerAccount.objects.filter(pk=request.user.pk).first()
        if not customer:
            return redirect("accounts:customer_login")

        target_id = request.POST.get("user_id")
        action = request.POST.get("action", "")

        if not target_id:
            return redirect("follows:customer_follower_list")

        target = get_object_or_404(CustomerAccount, pk=target_id)

        if target.pk == customer.pk:
            return redirect("follows:customer_follower_list")

        rel = Follow.objects.filter(follower=customer, followee=target).first()
        next_url = request.POST.get("next")

        # ✅ ミュート切り替え（フォロー関係がある時のみ）
        if action == "toggle_mute":
            if rel:
                rel.is_muted = not rel.is_muted
                rel.save(update_fields=["is_muted"])
            return redirect(next_url or "follows:customer_follower_list")

        # ✅ フォロー解除
        if action == "unfollow":
            if rel:
                rel.delete()
            return redirect(next_url or "follows:customer_follower_list")

        # ✅ フォローする（明示）
        if action == "follow":
            if not rel:
                try:
                    with transaction.atomic():
                        Follow.objects.get_or_create(follower=customer, followee=target)
                except IntegrityError:
                    pass
            return redirect(next_url or "follows:customer_follow_list")

        # ✅ 互換：action無し（従来のトグル動作）
        if rel:
            rel.delete()
            return redirect(next_url or "follows:customer_follower_list")

        try:
            with transaction.atomic():
                Follow.objects.get_or_create(follower=customer, followee=target)
        except IntegrityError:
            pass
        return redirect(next_url or "follows:customer_follow_list")


class Customer_follow_listView(LoginRequiredMixin, TemplateView):
    template_name = "follows/customer_follow_list.html"

    def _get_target_customer(self):
        customer_id = self.kwargs.get("customer_id")
        if customer_id:
            return get_object_or_404(CustomerAccount, pk=customer_id)
        return CustomerAccount.objects.filter(pk=self.request.user.pk).first()

    def _build_profile_context(self):
        target = self._get_target_customer()
        if not target:
            raise Http404("CustomerAccount not found")

        cover_field = getattr(target, "cover_image", None)
        icon_field = getattr(target, "icon_image", None)
        display_name = target.nickname or target.username
        readonly_mode = (target.pk != self.request.user.pk)

        return {
            "customer": target,
            "user_name": display_name,
            "profile_title": f"{display_name}のレストランガイド",
            "cover_image_url": cover_field.url if cover_field else "",
            "user_icon_url": icon_field.url if icon_field else "",
            "readonly_mode": readonly_mode,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._build_profile_context())

        customer = context["customer"]

        follow_rels = (
            Follow.objects
            .filter(follower=customer)
            .select_related("followee")
            .order_by("-followed_at")
        )

        viewer = CustomerAccount.objects.filter(pk=self.request.user.pk).first()
        follows = []
        for rel in follow_rels:
            card = _pack_user_card(viewer or customer, rel.followee)
            card["is_muted"] = rel.is_muted
            follows.append(card)

        context["follows"] = follows
        context["follow_count"] = len(follows)
        return context

    def post(self, request, *args, **kwargs):
        """
        フォロー中一覧の操作：
        - action=toggle_mute -> Follow.is_muted をトグル（adminにも反映）
        - action=unfollow    -> Follow削除（adminからも消える）
        """
        customer = CustomerAccount.objects.filter(pk=request.user.pk).first()
        if not customer:
            return redirect("accounts:customer_login")

        target_id = request.POST.get("user_id")
        action = request.POST.get("action", "")

        if not target_id:
            return redirect("follows:customer_follow_list")

        rel = Follow.objects.filter(follower=customer, followee_id=target_id).first()
        next_url = request.POST.get("next")

        if not rel:
            # フォローしていない場合でも、action=follow なら新規作成してnextへ（検索用拡張）
            if action == "follow":
                try:
                    with transaction.atomic():
                        Follow.objects.get_or_create(follower=customer, followee_id=target_id)
                except IntegrityError:
                    pass
            return redirect(next_url or "follows:customer_follow_list")

        if action == "toggle_mute":
            rel.is_muted = not rel.is_muted
            rel.save(update_fields=["is_muted"])
            return redirect(next_url or "follows:customer_follow_list")

        if action == "unfollow":
            rel.delete()
            return redirect(next_url or "follows:customer_follow_list")

        return redirect(next_url or "follows:customer_follow_list")
    
class Customer_user_pageView(LoginRequiredMixin, TemplateView):
    """
    フォロー一覧などから、対象ユーザーのマイページ（customer_reviewer_detail.html）を表示する
    """
    def get_template_names(self):
        # テンプレの置き場所が「reviews/配下」でも「直下」でも動くように両対応
        return [
            "reviews/customer_reviewer_detail.html",
            "customer_reviewer_detail.html",
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        target = get_object_or_404(CustomerAccount, pk=kwargs.get("customer_id"))

        cover_field = getattr(target, "cover_image", None)
        icon_field = getattr(target, "icon_image", None)

        # counts / stats（テンプレが参照している変数を全部埋める）
        count_reviews = Review.objects.filter(reviewer=target).count()
        count_following = Follow.objects.filter(follower=target).count()
        count_followers = Follow.objects.filter(followee=target).count()
        stats_photos = ReviewPhoto.objects.filter(review__reviewer=target).count()
        stats_likes = (
            Review.objects.filter(reviewer=target).aggregate(total=Sum("like_count")).get("total") or 0
        )
        # 訪問者数っぽいもの：ユニーク店舗数（無ければ0）
        stats_visitors = (
            Review.objects.filter(reviewer=target).values("store_id").distinct().count()
        )

        display_name = target.nickname or target.username

        context.update({
            "customer": target,
            "user_name": display_name,
            "cover_image_url": cover_field.url if cover_field else "",
            "user_icon_url": icon_field.url if icon_field else "",

            "stats_reviews": count_reviews,
            "stats_photos": stats_photos,
            "stats_visitors": stats_visitors,
            "stats_likes": stats_likes,

            "count_reviews": count_reviews,
            "count_following": count_following,
            "count_followers": count_followers,

            # ✅ 他人ページなので編集UIを出したくない場合に使う（任意）
            "readonly_mode": True,
        })
        return context

