from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.base import TemplateView
from django.views import View
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from commons.models import Review

class customer_common_completeView(TemplateView):
    template_name = "commons/customer_common_complete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # クエリパラメータ (?action=...&msg=...) を取得
        action = self.request.GET.get('action', 'update')
        msg = self.request.GET.get('msg', '完了しました。')

        context['action_type'] = action
        context['msg'] = msg
        
        # モードに応じたラベル設定
        labels = {'create': '登録', 'update': '変更', 'delete': '削除'}
        context['mode_label'] = labels.get(action, '処理')
        
        return context

class customer_common_confirmView(TemplateView):
    template_name = "commons/customer_common_confirm.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. 操作種別の定義 (create / update / delete)
        context['action_type'] = 'update' 
        context['mode_label'] = '登録内容の変更'
        
        # 2. 表示用データ (辞書形式で渡すと自動でテーブル化されます)
        context['display_data'] = [
            ('店舗名', '牛角 渋谷店', False),
            ('予約日時', '2024年12月24日 19:00', True), # 重要！
            ('人数', '4名', False),
            ('コース名', 'クリスマス限定食べ放題コース', True),
            ('合計金額', '¥24,000 (税込)', True),
        ]
        
        # 3. 実際にPOSTするデータ (hidden field用)
        context['hidden_data'] = {
            "customer_id": 101,
            "status": "active"
        }
        
        return context


class errorView(TemplateView):
    template_name = "commons/error.html"


class store_common_confirmView(TemplateView):
    template_name = "commons/store_common_confirm.html"


class store_common_completeView(TemplateView):
    template_name = "commons/store_common_complete.html"


# ✅ インデント修正：汎用の企業確認（今回は削除では使わない想定）
class company_common_confirmView(TemplateView):
    template_name = "commons/company_common_confirm.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["confirm_message"] = self.request.GET.get("message", "実行してよろしいですか？")

        referer = self.request.META.get("HTTP_REFERER")
        default_back_url = "/accounts/company/top/"
        context["cancel_url"] = referer if referer else default_back_url

        # OKボタンの action を渡さないとPOSTできないので、汎用confirmではダミーにしておく
        context["ok_action"] = self.request.GET.get("ok_action", "#")
        context["next_url"] = self.request.GET.get("next", default_back_url)
        return context


class company_common_completeView(TemplateView):
    template_name = "commons/company_common_complete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["display_message"] = self.request.GET.get("message", "処理")
        context["next_url"] = self.request.GET.get("next", "")
        return context


# ==========================================================
# ✅ 口コミ削除フロー（これが本番）
#   company_review_list → confirm → OK(POST) → complete
# ==========================================================

@method_decorator(login_required, name="dispatch")
class ReviewDeleteConfirmView(View):
    template_name = "commons/company_common_confirm.html"

    def get(self, request, review_id):
        review = get_object_or_404(
            Review.objects.select_related("reviewer", "store"),
            pk=review_id
        )

        next_url = request.GET.get("next")
        if (not next_url) or (not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})):
            next_url = reverse("reviews:company_review_list")

        context = {
            "confirm_message": "この口コミを削除します。よろしいですか？",
            "review": review,
            "ok_action": reverse("commons:review_delete_execute", args=[review_id]),
            "cancel_url": next_url,
            "next_url": next_url,
        }
        return render(request, self.template_name, context)


@method_decorator(login_required, name="dispatch")
class ReviewDeleteExecuteView(View):
    def post(self, request, review_id):
        review = get_object_or_404(Review, pk=review_id)
        review.delete()  # ✅ DBから消えるのでadmin側も消える

        next_url = request.POST.get("next_url") or reverse("reviews:company_review_list")
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            next_url = reverse("reviews:company_review_list")

        q = urlencode({"next": next_url, "message": "口コミ削除"})
        return redirect(f"{reverse('commons:review_delete_complete')}?{q}")


@method_decorator(login_required, name="dispatch")
class ReviewDeleteCompleteView(View):
    template_name = "commons/company_common_complete.html"

    def get(self, request):
        next_url = request.GET.get("next") or reverse("reviews:company_review_list")
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            next_url = reverse("reviews:company_review_list")

        context = {
            "display_message": request.GET.get("message", "処理"),
            "next_url": next_url,
        }
        return render(request, self.template_name, context)
