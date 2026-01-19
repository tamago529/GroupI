from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView


from commons.models import Review, ReviewReport,CustomerAccount, ReviewPhoto
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse

class customer_review_listView(TemplateView):
    template_name = "reviews/customer_review_list.html"


class customer_reviewer_review_listView(TemplateView):
    template_name = "reviews/customer_reviewer_review_list.html"


@method_decorator(login_required, name="dispatch")
class customer_reviewer_detailView(LoginRequiredMixin, DetailView):
    template_name = "reviews/customer_reviewer_detail.html"

    odel = CustomerAccount
    template_name = "reviews/customer_reviewer_detail.html"
    context_object_name = "customer"

    def get_object(self, queryset=None):
        user = self.request.user

        # ① 顧客以外は弾く（AccountType 名称はあなたのマスタに合わせて）
        if not getattr(user, "account_type", None) or user.account_type.account_type != "顧客":
            return None

        # ② CustomerAccount が存在するか（無ければ None）
        return CustomerAccount.objects.filter(pk=user.pk).first()

    def dispatch(self, request, *args, **kwargs):
        """
        get_object が None のときに DetailView は死ぬので、先に分岐して戻す
        """
        obj = self.get_object()
        if obj is None:
            return redirect("accounts:customer_login")  # 必要なら別ページに変更OK
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object

        # テンプレが期待してるキーに合わせて詰める
        context["user_name"] = customer.nickname

        # まだDBにカバー/アイコンのフィールドが無いなら空で渡す（テンプレ側でプレースホルダー）
        context["cover_image_url"] = getattr(customer, "cover_image_url", "")
        context["user_icon_url"] = getattr(customer, "icon_image_url", "")

        # 例：統計（必要な分だけ）
        context["stats_reviews"] = Review.objects.filter(reviewer=customer).count()
        context["stats_photos"] = ReviewPhoto.objects.filter(review__reviewer=customer).count()
        context["stats_visitors"] = 0
        context["stats_likes"] = customer.total_likes

        context["count_reviews"] = context["stats_reviews"]
        context["count_following"] = 0
        context["count_followers"] = 0

        return context


   
    def get_customer(self, request):
        # 多テーブル継承：request.user が Account の場合でも pk は共通
        return CustomerAccount.objects.get(pk=request.user.pk)

    def get(self, request, *args, **kwargs):
        customer = self.get_customer(request)

        context = {
            "user_name": customer.nickname,
            "cover_image_url": customer.cover_image.url if customer.cover_image else "",
            "user_icon_url": customer.icon_image.url if customer.icon_image else "",
            "stats_reviews": customer.review_count,
            "stats_photos": 0,
            "stats_visitors": 0,
            "stats_likes": customer.total_likes,
            "count_reviews": customer.review_count,
            "count_following": 0,
            "count_followers": 0,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        customer = self.get_customer(request)

        # ✅カバー更新
        if request.FILES.get("cover_image"):
            customer.cover_image = request.FILES["cover_image"]
            customer.save()
            return redirect(reverse("reviews:customer_reviewer_detail"))

        # ✅アイコン更新
        if request.FILES.get("icon_image"):
            customer.icon_image = request.FILES["icon_image"]
            customer.save()
            return redirect(reverse("reviews:customer_reviewer_detail"))

        return redirect(reverse("reviews:customer_reviewer_detail"))


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
