from django.shortcuts import render

from django.views.generic.base import TemplateView

class customer_common_completeView(TemplateView):
    template_name = 'commons/customer_common_complete.html'

class customer_common_confirmView(TemplateView):
    template_name = 'commons/customer_common_confirm.html'

class errorView(TemplateView):
    template_name = 'commons/error.html'

class store_common_confirmView(TemplateView):
    template_name = 'commons/store_common_confirm.html'

class store_common_completeView(TemplateView):
    template_name = 'commons/store_common_complete.html'

# company_common_confirmView後で修正する可能性大です。福原
class company_common_confirmView(TemplateView):
    template_name = 'commons/company_common_confirm.html' 
def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1. 確認メッセージ（URLの ?message= から取得）
        # 例: /commons/company/confirm/?message=このアカウントを削除しますか？
        context['confirm_message'] = self.request.GET.get('message', '実行してよろしいですか？')

        # 2. キャンセル時の戻り先（方法3：HTTP_REFERER）
        # 直前にいたページのURLを自動取得します。
        referer = self.request.META.get('HTTP_REFERER')
        
        # もし「戻り先」が取得できなかった場合の予備（運用トップなど）
        default_back_url = '/accounts/company/top/' 
        
        context['cancel_url'] = referer if referer else default_back_url

        # 3. OKボタンを押した時の遷移先（URLの ?next_url= から取得）
        # 完了画面のURLなどを渡す想定です。
        context['next_url'] = self.request.GET.get('next_url', '#')

        return context

class company_common_completeView(TemplateView):
    template_name = 'commons/company_common_complete.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # URLの ?message=◯◯ を取得。なければデフォルトを表示
        message = self.request.GET.get('message', '処理')
        context['display_message'] = message
        return context