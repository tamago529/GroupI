from django.shortcuts import render
from django.views.generic.base import TemplateView

from commons.models import Review, ReviewReport

class customer_review_listView(TemplateView):
    template_name = "reviews/customer_review_list.html"


class customer_reviewer_review_listView(TemplateView):
    template_name = "reviews/customer_reviewer_review_list.html"


class customer_reviewer_detailView(TemplateView):
    template_name = "reviews/customer_reviewer_detail.html"


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
