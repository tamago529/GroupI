from django.shortcuts import render, get_object_or_404
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView,View


from commons.models import Review, ReviewReport,CustomerAccount, ReviewPhoto
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse

class customer_review_listView(TemplateView):
    template_name = "reviews/customer_review_list.html"


class customer_reviewer_review_listView(TemplateView):
    template_name = "reviews/customer_reviewer_review_list.html"

class customer_reviewer_detail_selfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return redirect(reverse("reviews:customer_reviewer_detail", args=[request.user.pk]))


class customer_reviewer_detailView(View):
    template_name = "reviews/customer_reviewer_detail.html"

    def _get_customer(self, request):
        """
        ログイン未実装前提：
        - ?customer_id=xx があればそれを優先
        - なければ CustomerAccount の先頭1件
        - それも無ければ None
        """
        cid = request.GET.get("customer_id") or request.POST.get("customer_id")
        if cid:
            customer = CustomerAccount.objects.filter(pk=cid).first()
            if customer:
                return customer

        return CustomerAccount.objects.order_by("pk").first()

    def get(self, request, *args, **kwargs):
        customer = self._get_customer(request)

        # CustomerAccount が1件も無い場合でも落とさない
        if customer is None:
            context = {
                "customer": None,
                "user_name": "ゲスト",
                "cover_image_url": "",
                "user_icon_url": "",
                "stats_reviews": 0,
                "stats_photos": 0,
                "stats_visitors": 0,
                "stats_likes": 0,
                "count_reviews": 0,
                "count_following": 0,
                "count_followers": 0,
            }
            return render(request, self.template_name, context)

        cover_field = getattr(customer, "cover_image", None)
        icon_field = getattr(customer, "icon_image", None)

        context = {
            "customer": customer,
            "user_name": customer.nickname,
            "cover_image_url": cover_field.url if cover_field else "",
            "user_icon_url": icon_field.url if icon_field else "",

            "stats_reviews": Review.objects.filter(reviewer=customer).count(),
            "stats_photos": ReviewPhoto.objects.filter(review__reviewer=customer).count(),
            "stats_visitors": 0,
            "stats_likes": customer.total_likes,

            "count_reviews": Review.objects.filter(reviewer=customer).count(),
            "count_following": 0,
            "count_followers": 0,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        customer = self._get_customer(request)
        if customer is None:
            # そもそも更新対象がない
            return redirect(reverse("reviews:customer_reviewer_detail"))

        # ✅ カバー更新
        if request.FILES.get("cover_image") and hasattr(customer, "cover_image"):
            customer.cover_image = request.FILES["cover_image"]
            customer.save()

        # ✅ アイコン更新
        if request.FILES.get("icon_image") and hasattr(customer, "icon_image"):
            customer.icon_image = request.FILES["icon_image"]
            customer.save()

        # 更新後も同じ人を見せたい（customer_id を維持）
        return redirect(f"{reverse('reviews:customer_reviewer_detail')}?customer_id={customer.pk}")


class customer_reviewer_searchView(TemplateView):
    template_name = "reviews/customer_reviewer_search.html"


class customer_review_reportView(TemplateView):
    template_name = "reviews/customer_review_report.html"


class store_review_reportView(TemplateView):
    template_name = "reviews/store_review_report.html"


class store_review_listView(TemplateView):
    template_name = "reviews/store_review_list.html"


class company_review_listView(TemplateView):
    template_name = "reviews/company_review_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ✅ チェックONなら "reported=1" をURLに付ける想定
        only_reported = self.request.GET.get("reported") == "1"

        # ✅ 通報済みID（バッジ表示・JS用）
        reported_review_ids = (
            ReviewReport.objects
            .filter(report_status=True)
            .values_list("review_id", flat=True)
            .distinct()
        )

        # ✅ 一覧（チェック状態で切り替え）
        qs = Review.objects.select_related("reviewer", "store").all()

        if only_reported:
            qs = qs.filter(reviewreport__report_status=True).distinct()

        reviews = qs.order_by("-posted_at")

        context["reviews"] = reviews
        context["reported_review_ids"] = reported_review_ids
        context["only_reported"] = only_reported  # テンプレでchecked制御に使う
        return context
        


class customer_report_input(TemplateView):
    template_name = "reviews/customer_report_input.html"


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
