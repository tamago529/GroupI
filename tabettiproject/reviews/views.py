# reviews/views.py（コピペ用：整理済み完全版）

from __future__ import annotations

import urllib.parse
from datetime import date, time

from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Max, Count, Q, Exists, OuterRef
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView
from django.views.generic.base import TemplateView

from commons.models import (
    CustomerAccount,
    Store,
    Reservator,
    Reservation,
    ReservationStatus,
    Review,
    ReviewPhoto,
    ReviewReport,
    StoreInfoReport,
    StoreInfoReportPhoto,
    Follow,
    Genre,
)


class customer_review_listView(View):
    """
    口コミ一覧（誰でも閲覧OK）
    - 保存・投稿はログイン必須
    - 共通ヘッダー（_customer_store_common.html）対応：
      context に store / is_saved / avg_rating / review_count / star_states を入れる
    """
    template_name = "reviews/customer_review_list.html"

    # ---------------------------------
    # ログイン顧客取得（継承モデル対策：pkで引き直し）
    # ---------------------------------
    def _get_login_customer(self, request):
        if not request.user.is_authenticated:
            return None
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    # ---------------------------------
    # 表示対象店舗取得
    # ---------------------------------
    def _get_store(self, request):
        sid = request.GET.get("store_id") or request.POST.get("store_id")

        # pk ルートにも対応（保険）
        if not sid and "pk" in self.kwargs:
            sid = self.kwargs["pk"]

        if sid:
            store = Store.objects.filter(pk=sid).first()
            if store:
                return store

        # フェイルセーフ（とりあえず1件）
        return Store.objects.order_by("pk").first()

    # ---------------------------------
    # 星状態生成（★/半★/☆）
    # ---------------------------------
    def _build_star_states(self, avg_rating: float) -> list[str]:
        """
        星のルール（確定）:
        - 2.0 -> ★★☆☆☆
        - 2.5〜2.9 -> ★★☆½☆
        - 2.9以上 -> 繰り上げ（★★★☆☆）
        """
        rating = float(avg_rating or 0.0)

        full = int(rating)
        frac = rating - full

        if frac >= 0.9:
            full += 1
            half = 0
        elif frac >= 0.5:
            half = 1
        else:
            half = 0

        if full >= 5:
            full = 5
            half = 0

        empty = max(0, 5 - full - half)
        return (["full"] * full) + (["half"] * half) + (["empty"] * empty)

    # =================================
    # GET：口コミ一覧表示
    # =================================
    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        store = self._get_store(request)

        store_reviews = Review.objects.none()
        avg_rating = 0.0
        review_count = 0
        star_states = ["empty"] * 5

        if store:
            store_reviews = (
                Review.objects
                .select_related("reviewer")
                .filter(store=store)
                .order_by("-posted_at")
            )

            # 全件の集計（検索フィルタ前に計算）
            agg = store_reviews.aggregate(avg=Avg("score"))
            avg_rating = float(agg["avg"] or 0.0)
            review_count = store_reviews.count()

            # ★ キーワード検索（本文・タイトル）
            review_keyword = request.GET.get("review_keyword", "").strip()
            if review_keyword:
                store_reviews = store_reviews.filter(review_text__icontains=review_keyword)

            star_states = self._build_star_states(avg_rating)

        # 保存済み判定（ログイン時のみ）
        is_saved = False
        if customer and store:
            saved_status = ReservationStatus.objects.filter(status="保存済み").first()
            reservator = Reservator.objects.filter(customer_account=customer).first()
            if saved_status and reservator:
                is_saved = Reservation.objects.filter(
                    booking_user=reservator,
                    store=store,
                    booking_status=saved_status,
                ).exists()

        context = {
            # 共通ヘッダー用（★ここが重要）
            "store": store,
            "is_saved": is_saved,
            "avg_rating": avg_rating,
            "review_count": review_count,
            "star_states": star_states,

            # 一覧用
            "reviews": store_reviews,
            "customer": customer,
            "store_id": store.pk if store else "",
            # 共通ヘッダーのタブ制御を使っているなら渡す
            "active_main": "reviews",
            "active_sub": "top",
            "keyword": request.GET.get("keyword", ""),
            "area": request.GET.get("area", ""),
            "date": request.GET.get("date", ""),
            "time": request.GET.get("time", ""),
            "sort": request.GET.get("sort", ""),
            "from_search": request.GET.get("from_search", ""),
            "review_keyword": request.GET.get("review_keyword", ""),
        }
        return render(request, self.template_name, context)

    # =================================
    # POST：保存 / 口コミ投稿
    # =================================
    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        customer = self._get_login_customer(request)

        # ログイン必須
        if customer is None:
            messages.error(request, "その機能を利用するには顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        store_id = request.POST.get("store_id")
        store = Store.objects.filter(pk=store_id).first() if store_id else None

        if store is None:
            messages.error(request, "店舗情報が取得できませんでした。")
            return redirect(reverse("reviews:customer_review_list"))

        # -----------------------------
        # 保存処理
        # -----------------------------
        if action == "save_store":
            saved_status, _ = ReservationStatus.objects.get_or_create(status="保存済み")
            reservator, _ = Reservator.objects.get_or_create(
                customer_account=customer,
                defaults={
                    "full_name": customer.nickname,
                    "full_name_kana": customer.nickname,
                    "email": customer.sub_email,
                    "phone_number": customer.phone_number,
                }
            )

            exists = Reservation.objects.filter(
                booking_user=reservator,
                store=store,
                booking_status=saved_status,
            ).exists()

            if exists:
                messages.info(request, "すでに保存済みです。")
            else:
                Reservation.objects.create(
                    booking_user=reservator,
                    store=store,
                    booking_status=saved_status,
                    visit_date=date.today(),
                    visit_time=time(0, 0),
                    visit_count=1,
                    course="保存",
                )
                messages.success(request, "保存しました。")

            params = {
                "store_id": store.pk,
                "keyword": request.GET.get("keyword", ""),
                "area": request.GET.get("area", ""),
                "date": request.GET.get("date", ""),
                "time": request.GET.get("time", ""),
                "sort": request.GET.get("sort", ""),
                "from_search": request.GET.get("from_search", ""),
            }
            # 空のパラメータを除外
            query_string = urllib.parse.urlencode({k: v for k, v in params.items() if v})
            return redirect(f"{reverse('reviews:customer_review_list')}?{query_string}")

        # -----------------------------
        # 口コミ投稿処理
        # -----------------------------
        if action == "create_review":
            time_slot = (request.POST.get("time_slot") or "").strip()
            score_raw = (request.POST.get("score") or "").strip()
            title = (request.POST.get("title") or "").strip()
            body = (request.POST.get("body") or "").strip()
            agree = request.POST.get("agree")

            try:
                score = int(score_raw)
            except ValueError:
                score = 0

            if (
                time_slot not in ("昼", "夜")
                or score < 1
                or not title
                or not body
                or not agree
            ):
                messages.error(request, "入力内容に不備があります。")
                params = {
                    "store_id": store.pk,
                    "keyword": request.GET.get("keyword", ""),
                    "area": request.GET.get("area", ""),
                    "date": request.GET.get("date", ""),
                    "time": request.GET.get("time", ""),
                    "sort": request.GET.get("sort", ""),
                    "from_search": request.GET.get("from_search", ""),
                }
                query_string = urllib.parse.urlencode({k: v for k, v in params.items() if v})
                return redirect(f"{reverse('reviews:customer_review_list')}?{query_string}")

            review_obj = Review.objects.create(
                reviewer=customer,
                store=store,
                score=score,
                review_text=f"【{time_slot}】{title}\n{body}",
            )

            files = request.FILES.getlist('photos')
            
            # 最大5枚まで保存する
            for f in files[:5]:
                ReviewPhoto.objects.create(
                    review=review_obj, # さっき作った口コミと紐付け
                    image_path=f        # commons/models.pyのフィールド名に合わせる
                )

            messages.success(request, "口コミを投稿しました。")

            params = {
                "store_id": store.pk,
                "keyword": request.GET.get("keyword", ""),
                "area": request.GET.get("area", ""),
                "date": request.GET.get("date", ""),
                "time": request.GET.get("time", ""),
                "sort": request.GET.get("sort", ""),
                "from_search": request.GET.get("from_search", ""),
            }
            query_string = urllib.parse.urlencode({k: v for k, v in params.items() if v})
            return redirect(f"{reverse('reviews:customer_review_list')}?{query_string}")

        return redirect(reverse("reviews:customer_review_list"))


class customer_store_preserveView(LoginRequiredMixin, View):
    template_name = "reviews/customer_store_preserve.html"

    def _get_login_customer(self, request):
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)

        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        # 1. パラメータ取得
        genre_id = request.GET.get("genre")
        min_budget = request.GET.get("min_budget")
        max_budget = request.GET.get("max_budget")
        went_status = request.GET.get("went", "any")

        # 2. 基本セットアップ
        saved_status = ReservationStatus.objects.filter(status="保存済み").first()
        if saved_status is None:
            return render(request, self.template_name, {"customer": customer, "saved_list": []})

        reservator = Reservator.objects.filter(customer_account=customer).first()
        if reservator is None:
            return render(request, self.template_name, {"customer": customer, "saved_list": []})

        # 3. クエリセット構築
        queryset = (
            Reservation.objects
            .select_related("store", "booking_status", "store__area", "store__scene")
            .filter(booking_user=reservator, booking_status=saved_status)
        )

        # --- フィルタ適用 ---
        # ジャンル
        if genre_id and genre_id != "all":
            queryset = queryset.filter(store__genre_master_id=genre_id)

        # 予算
        if min_budget and min_budget.isdigit():
            queryset = queryset.filter(store__budget__gte=int(min_budget))
        if max_budget and max_budget.isdigit():
            queryset = queryset.filter(store__budget__lte=int(max_budget))

        # 行った・行ってない
        if went_status in ("yes", "no"):
            # 「行った」判定：口コミがある or 「保存済み」以外の予約がある
            has_review = Review.objects.filter(reviewer=customer, store=OuterRef('store_id'))
            has_other_res = Reservation.objects.filter(
                booking_user=reservator, 
                store=OuterRef('store_id')
            ).exclude(booking_status=saved_status)
            
            queryset = queryset.annotate(
                went_flag=Exists(has_review) | Exists(has_other_res)
            )

            if went_status == "yes":
                queryset = queryset.filter(went_flag=True)
            else:
                queryset = queryset.filter(went_flag=False)

        saved_list = queryset.order_by("-created_at")

        # 4. サイドバー用データ
        genres = Genre.objects.all().order_by("name")
        budget_choices = [1000, 2000, 3000, 4000, 5000, 10000, 15000, 20000, 30000]

        context = {
            "customer": customer,
            "saved_list": saved_list,
            "genres": genres,
            "budget_choices": budget_choices,
            # 現在の選択状態
            "selected_genre": genre_id,
            "selected_min": min_budget,
            "selected_max": max_budget,
            "selected_went": went_status,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action") or ""
        reservation_id = request.POST.get("reservation_id")

        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        if action == "remove_store" or reservation_id:
            if not reservation_id:
                messages.warning(request, "保存解除に必要な情報が不足しています。")
                return redirect(reverse("reviews:customer_store_preserve"))

            saved_status = ReservationStatus.objects.filter(status="保存済み").first()

            deleted, _ = Reservation.objects.filter(
                id=reservation_id,
                booking_user__customer_account=customer,
                booking_status=saved_status,
            ).delete()

            if deleted > 0:
                messages.success(request, "保存解除しました。")
            else:
                messages.warning(request, "対象の保存データが見つかりませんでした。")

            return redirect(reverse("reviews:customer_store_preserve"))

        return redirect(reverse("reviews:customer_store_preserve"))


class customer_reviewer_detailView(LoginRequiredMixin, View):
    template_name = "reviews/customer_reviewer_detail.html"

    def _get_login_customer(self, request):
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)

        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        cover_field = getattr(customer, "cover_image", None)
        icon_field = getattr(customer, "icon_image", None)

        count_reviews = Review.objects.filter(reviewer=customer).count()
        count_following = Follow.objects.filter(follower=customer).count()
        count_followers = Follow.objects.filter(followee=customer).count()

        context = {
            "customer": customer,
            "user_name": customer.nickname or request.user.username,
            "cover_image_url": cover_field.url if cover_field else "",
            "user_icon_url": icon_field.url if icon_field else "",

            "stats_reviews": count_reviews,
            "stats_photos": ReviewPhoto.objects.filter(review__reviewer=customer).count(),
            "stats_visitors": 0,
            "stats_likes": getattr(customer, "total_likes", 0),

            "count_reviews": count_reviews,
            "count_following": count_following,
            "count_followers": count_followers,

            "latest_reviews": Review.objects.filter(reviewer=customer).order_by("-posted_at")[:3],
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        if request.FILES.get("cover_image") and hasattr(customer, "cover_image"):
            customer.cover_image = request.FILES["cover_image"]
            customer.save(update_fields=["cover_image"])

        if request.FILES.get("icon_image") and hasattr(customer, "icon_image"):
            customer.icon_image = request.FILES["icon_image"]
            customer.save(update_fields=["icon_image"])

        return redirect(reverse("reviews:customer_reviewer_detail"))


class customer_reviewer_detail_selfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return redirect(reverse("reviews:customer_reviewer_detail", args=[request.user.pk]))


class customer_reviewer_review_listView(LoginRequiredMixin, View):
    template_name = "reviews/customer_reviewer_review_list.html"

    def _get_login_customer(self, request):
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def get(self, request, *args, **kwargs):
        customer_id = kwargs.get("customer_id")
        if customer_id:
            customer = get_object_or_404(CustomerAccount, pk=customer_id)
            readonly_mode = (customer.pk != request.user.pk)
        else:
            customer = self._get_login_customer(request)
            readonly_mode = False

        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        cover_field = getattr(customer, "cover_image", None)
        icon_field = getattr(customer, "icon_image", None)

        # 1. パラメータ取得
        genre_id = request.GET.get("genre")
        min_budget = request.GET.get("min_budget")
        max_budget = request.GET.get("max_budget")

        my_reviews_qs = (
            Review.objects
            .select_related("store", "store__genre_master")
            .filter(reviewer=customer)
        )

        # --- フィルタ適用 ---
        # ジャンル
        if genre_id and genre_id != "all":
            my_reviews_qs = my_reviews_qs.filter(store__genre_master_id=genre_id)

        # 予算
        if min_budget and min_budget.isdigit():
            my_reviews_qs = my_reviews_qs.filter(store__budget__gte=int(min_budget))
        if max_budget and max_budget.isdigit():
            my_reviews_qs = my_reviews_qs.filter(store__budget__lte=int(max_budget))

        my_reviews = my_reviews_qs.order_by("-posted_at")

        reviewed_store_rows = (
            Review.objects
            .filter(reviewer=customer)
            .values("store_id", "store__store_name", "store__branch_name")
            .annotate(
                latest_posted_at=Max("posted_at"),
                visit_count=Count("id"),
            )
            .order_by("-latest_posted_at")
        )

        store_choices = Store.objects.order_by("store_name", "branch_name")
        genres = Genre.objects.all().order_by("name")
        budget_choices = [1000, 2000, 3000, 4000, 5000, 10000, 15000, 20000, 30000]

        context = {
            "customer": customer,
            "user_name": customer.nickname,
            "cover_image_url": cover_field.url if cover_field else "",
            "user_icon_url": icon_field.url if icon_field else "",
            "readonly_mode": readonly_mode,

            "reviewed_store_list": reviewed_store_rows,
            "reviewed_total": reviewed_store_rows.count(),

            "my_reviews": my_reviews,
            "my_reviews_total": my_reviews.count(),

            "store_choices": store_choices,
            "genres": genres,
            "budget_choices": budget_choices,

            # 現在の選択状態
            "selected_genre": genre_id,
            "selected_min": min_budget,
            "selected_max": max_budget,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        action = request.POST.get("action")

        if action == "create_review":
            store_id = request.POST.get("store_id")
            store = Store.objects.filter(pk=store_id).first() if store_id else None
            if store is None:
                messages.error(request, "店舗を選択してください。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            score_raw = (request.POST.get("score") or "").strip()
            title = (request.POST.get("title") or "").strip()
            body = (request.POST.get("body") or "").strip()
            agree = request.POST.get("agree")

            try:
                score = int(score_raw)
            except ValueError:
                score = 0



            if score < 1 or score > 5:
                messages.error(request, "星評価（1〜5）を選択してください。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            if not title:
                messages.error(request, "タイトルを入力してください。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            if not body:
                messages.error(request, "本文を入力してください。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            if not agree:
                messages.error(request, "同意にチェックしてください。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            review_text = f"{title}\n{body}"

            Review.objects.create(
                reviewer=customer,
                store=store,
                score=score,
                review_text=review_text,
            )

            messages.success(request, "口コミを投稿しました。")
            return redirect(reverse("reviews:customer_reviewer_review_list"))

        if action == "delete_review":
            review_id = request.POST.get("review_id")
            if not review_id:
                messages.error(request, "削除対象の口コミが取得できませんでした。")
                return redirect(reverse("reviews:customer_reviewer_review_list"))

            deleted, _ = Review.objects.filter(
                id=review_id,
                reviewer=customer,
            ).delete()

            if deleted == 0:
                messages.error(request, "削除できませんでした（他ユーザーの口コミ、または存在しません）。")
            else:
                messages.success(request, "口コミを削除しました。")

            return redirect(reverse("reviews:customer_reviewer_review_list"))

        return redirect(reverse("reviews:customer_reviewer_review_list"))


class customer_reviewer_searchView(LoginRequiredMixin, View):
    template_name = "reviews/customer_reviewer_search.html"

    def _get_login_customer(self, request):
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        keyword = request.GET.get("keyword", "").strip()
        
        # 検索結果の初期化
        search_results = []
        result_count = 0

        if keyword:
            # キーワードによる口コミ検索（タイトル、本文、店舗名、レビュアー名）
            from django.db.models import Q
            
            search_results = (
                Review.objects
                .select_related("store", "reviewer")
                .filter(
                    Q(review_title__icontains=keyword) |
                    Q(review_text__icontains=keyword) |
                    Q(store__store_name__icontains=keyword) |
                    Q(reviewer__nickname__icontains=keyword)
                )
                .order_by("-posted_at")
            )
            result_count = search_results.count()

        context = {
            "customer": customer,
            "keyword": keyword,
            "search_results": search_results,
            "result_count": result_count,
        }
        return render(request, self.template_name, context)


class customer_review_reportView(LoginRequiredMixin, View):
    template_name = "reviews/customer_review_report.html"

    def _get_login_customer(self, request):
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        context = {
            "customer": customer,
            "display_nickname": customer.nickname,
            "display_email": customer.sub_email or customer.email,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "ユーザー情報が取得できませんでした。")
            return redirect(reverse("reviews:customer_review_report"))

        message = (request.POST.get("message") or "").strip()
        user_type = (request.POST.get("user_type") or "").strip()
        agree = request.POST.get("agree")

        if not message:
            messages.error(request, "お問い合わせ内容をご記入ください。")
            return redirect(reverse("reviews:customer_review_report"))

        if user_type not in ("1", "2", "3"):
            messages.error(request, "ご入力者を選択してください。")
            return redirect(reverse("reviews:customer_review_report"))

        if not agree:
            messages.error(request, "同意事項にチェックしてください。")
            return redirect(reverse("reviews:customer_review_report"))

        user_type_label = {"1": "一般ユーザー", "2": "飲食店関係者", "3": "その他"}.get(user_type, "-")
        now_str = timezone.localtime(timezone.now()).strftime("%Y/%m/%d %H:%M")

        entry = (
            f"【{now_str}】入力者:{user_type_label}\n"
            f"ニックネーム:{customer.nickname}\n"
            f"メール:{(customer.sub_email or customer.email)}\n"
            f"内容:\n{message}\n"
            f"------------------------------\n"
        )

        customer.inquiry_log = entry + (customer.inquiry_log or "")
        customer.save(update_fields=["inquiry_log"])

        return redirect(f"{reverse('reviews:customer_common_completeView')}?msg={urllib.parse.quote('問い合わせが完了しました。')}")


class store_review_reportView(TemplateView):
    template_name = "reviews/store_review_report.html"

    def get(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        return render(request, self.template_name, {"review": review})

    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        report_text = request.POST.get("report_text")

        if not report_text:
            messages.error(request, "通報理由を入力してください。")
            return render(request, self.template_name, {"review": review})

        ReviewReport.objects.create(
            review=review,
            reporter=request.user,
            report_text=report_text,
            report_status=False
        )

        messages.success(request, "口コミを通報しました。運営にて内容を確認いたします。")
        return redirect("reviews:store_review_list",pk=review.store.pk)


class store_review_listView(LoginRequiredMixin, ListView):
    model = Review
    template_name = "reviews/store_review_list.html"
    context_object_name = "reviews"

    def get_queryset(self):
        try:
            user_store = self.request.user.storeaccount.store
            return (
                Review.objects
                .filter(store=user_store)
                .select_related("reviewer")
                .order_by("-posted_at")
            )
        except AttributeError:
            return Review.objects.none()


class company_review_listView(TemplateView):
    template_name = "reviews/company_review_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        only_reported = self.request.GET.get("reported") == "1"

        reported_review_ids = (
            ReviewReport.objects
            .filter(report_status=True)
            .values_list("review_id", flat=True)
            .distinct()
        )

        qs = Review.objects.select_related("reviewer", "store").all()

        if only_reported:
            qs = qs.filter(reviewreport__report_status=True).distinct()

        context["reviews"] = qs.order_by("-posted_at")
        context["reported_review_ids"] = reported_review_ids
        context["only_reported"] = only_reported
        return context
    
def review_delete_execute(request, pk):
    # ① 口コミを削除
    review = get_object_or_404(Review, pk=pk)
    review.delete()
    
    # ② 完了画面へリダイレクト
    msg = "口コミの削除"
    return redirect(reverse('commons:company_common_complete') + f"?msg={urllib.parse.quote(msg)}")


class customer_report_input(LoginRequiredMixin, View):
    template_name = "reviews/customer_report_input.html"

    def _get_login_customer(self, request):
        return CustomerAccount.objects.filter(pk=request.user.pk).first()

    def get(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            messages.error(request, "顧客アカウントでログインしてください。")
            return redirect(reverse("accounts:customer_login"))

        review_id = request.GET.get("review_id")
        store_id = request.GET.get("store_id")

        target_review = Review.objects.filter(pk=review_id).first() if review_id else None
        store = Store.objects.filter(pk=store_id).first() if store_id else None

        if target_review:
            store = target_review.store

        return render(request, self.template_name, {
            "customer": customer,
            "store": store,
            "target_review": target_review
        })

    def post(self, request, *args, **kwargs):
        customer = self._get_login_customer(request)
        if customer is None:
            return redirect(reverse("accounts:customer_login"))

        message = (request.POST.get("comment") or "").strip()
        agree = request.POST.get("agree")
        review_id = request.POST.get("review_id")
        store_id = request.POST.get("store_id")

        if not message or not agree:
            messages.error(request, "未入力の項目、または同意が必要です。")
            return redirect(request.path + f"?review_id={review_id or ''}&store_id={store_id or ''}")

        if review_id:
            review = get_object_or_404(Review, pk=review_id)
            ReviewReport.objects.create(
                review=review,
                reporter=request.user,
                report_text=message,
                report_status=False
            )
            msg = "口コミの通報が完了しました。"
        else:
            msg = "店舗情報の報告が完了しました。"

        return redirect(f"{reverse('commons:customer_common_complete')}?msg={urllib.parse.quote(msg)}&action=create")


class reportView(TemplateView):
    template_name = "reviews/report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reports = (
            ReviewReport.objects
            .select_related("review", "reporter", "review__reviewer")
            .all()
            .order_by("-reported_at")
        )
        context["reports"] = reports
        return context

def review_delete_execute(request, pk):
    # ① 対象の口コミを取得して削除
    review = get_object_or_404(Review, pk=pk)
    review.delete()
    
    # ② 共通完了画面へ（msgパラメータを使用）
    msg = "不適切な口コミの削除"
    return redirect(reverse('commons:company_common_complete') + f"?msg={urllib.parse.quote(msg)}&action=delete")
    

class customer_common_completeView(View):
    template_name = "commons/customer_common_complete.html"

    def get(self, request, *args, **kwargs):
        msg = request.GET.get("msg", "完了しました。")
        return render(request, self.template_name, {"msg": msg})

def toggle_review_like(request, pk):
    # ログインしていない場合は403エラーを返す
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'login_required'}, status=403)

    review = get_object_or_404(Review, pk=pk)
    user = request.user

    # 🌟 すでに「いいね」リストの中に自分がいるか判定
    if user in review.liked_users.all():
        review.liked_users.remove(user) # リストから削除
        liked = False
    else:
        review.liked_users.add(user) # リストに追加
        liked = True

    # 🌟 数のカウントを更新して保存
    review.like_count = review.liked_users.count()
    review.save()

    return JsonResponse({
        'liked': liked,
        'total_likes': review.like_count
    })