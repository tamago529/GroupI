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
        # ① すべての口コミを取得（投稿が新しい順）
        # select_relatedを使うと、投稿者(reviewer)や店舗(store)のデータも一緒に取れるので動作が速くなります
        reviews = Review.objects.select_related('reviewer', 'store').all().order_by('-posted_at')
        
        # ② 「どの口コミが通報されているか」のIDリストを取得（チェックボックス用）
        reported_review_ids = ReviewReport.objects.values_list('review_id', flat=True).distinct()
        
        context['reviews'] = reviews
        context['reported_review_ids'] = reported_review_ids
        return context


class customer_report_input(TemplateView):
    template_name = "reviews/customer_report_input.html"

class reportView(TemplateView):
    template_name = "reviews/report.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ① すべての通報（Report）を取得
        # 通報者(reporter)と、通報された口コミ(review)のデータをまとめて取得
        reports = ReviewReport.objects.select_related('review', 'reporter', 'review__reviewer').all().order_by('-reported_at')
        
        context['reports'] = reports
        return context
