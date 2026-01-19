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

        # ① 「通報済み（adminでONにされた）」口コミだけを取得（新しい順）
        reviews = (
            Review.objects
            .select_related("reviewer", "store")
            .filter(reviewreport__report_status=True)
            .distinct()
            .order_by("-posted_at")
        )

        # ② 「通報済み口コミID」リスト（チェックボックス用）
        reported_review_ids = (
            ReviewReport.objects
            .filter(report_status=True)
            .values_list("review_id", flat=True)
            .distinct()
        )

        context["reviews"] = reviews
        context["reported_review_ids"] = reported_review_ids
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
