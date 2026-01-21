from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login ,logout
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView

from commons.models import StoreAccount,Account
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy, reverse # 追加
from django.contrib import messages                         # エラー表示用
from django.db.models import Q
from django.views.generic import ListView
from .forms import CustomerLoginForm
from django.contrib.auth.views import PasswordResetView , PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
#共通機能の定義

class company_account_managementView(ListView):
    template_name = "accounts/company_account_management.html"
    model = Account
    context_object_name = "accounts"

    def get_queryset(self):
        queryset = super().get_queryset().select_related('account_type')
        
        # 1. 検索ワード
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(username__icontains=q) | 
                Q(email__icontains=q) |
                Q(customeraccount__nickname__icontains=q)
            )

        # 2. アカウント種別絞り込み（ラジオボタン形式に対応）
        # getlist ではなく get で単一の値として取得します
        selected_type = self.request.GET.get('type', 'all') 
        
        if selected_type == 'customer':
            queryset = queryset.filter(account_type__account_type='顧客')
        elif selected_type == 'store':
            queryset = queryset.filter(account_type__account_type='店舗')
        # 'all' の場合は filter をかけずに全件表示

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        # 現在選択されている値をテンプレートに返す（デフォルトは 'all'）
        context['selected_type'] = self.request.GET.get('type', 'all')
        return context
    
class company_loginView(LoginView):
    template_name = "accounts/company_login.html"

     # ログイン成功時のリダイレクト先
    def get_success_url(self):
        return reverse_lazy('accounts:company_top')

    # ログインボタンが押された後のチェック処理
    def form_valid(self, form):
        user = form.get_user()
        # ログインしたユーザーが「企業（運用管理側）」かチェック
        # マスタデータ（AccountType）の名称が「企業」の場合
        if user.account_type.account_type != "企業":
            messages.error(self.request, "運用管理アカウント以外はログインできません。")
            return self.form_invalid(form)
        
        return super().form_valid(form)

def company_logout_view(request):
    logout(request) # ここで実際にログアウト処理を実行
    return render(request, "accounts/company_logout.html") # ログアウト完了画面を表示

    

class company_store_review_detailView(TemplateView):
    template_name = "accounts/company_store_review_detail.html"

class company_store_reviewView(TemplateView):
    template_name = "accounts/company_store_review.html"

class company_topView(TemplateView):
    template_name = "accounts/company_top.html"       

class customer_loginView(LoginView):
    template_name = "accounts/customer_login.html"
    authentication_form = CustomerLoginForm # 🌟作成したメール用フォームを指定

    def get_success_url(self):
        # ログイン成功後は顧客トップへ
        return reverse_lazy('accounts:customer_top')

    def form_valid(self, form):
        user = form.get_user()
        # ★顧客ユーザー（CustomerAccount）かチェック
        try:
            _ = user.customeraccount
        except:
            messages.error(self.request, "顧客アカウントではありません。")
            return self.form_invalid(form)
        
        return super().form_valid(form)

# --- 顧客ログアウト ---
def customer_logout_view(request):
    logout(request)
    return redirect("accounts:customer_login")

#class customer_logoutView(TemplateView):
#    template_name = "accounts/customer_logout.html"

class customer_registerView(TemplateView):
    template_name = "accounts/customer_register.html"

class customer_settingsView(TemplateView):
    template_name = "accounts/customer_settings.html"

class customermail_sendView(PasswordResetView):
    template_name = "accounts/customer_mail_send.html"
    email_template_name = "accounts/password_reset_email.html"
    success_url = reverse_lazy('accounts:customer_password_done') # 送信完了画面へ

class customer_password_reset_completeView(PasswordResetCompleteView):
    template_name = "accounts/customer_password_reset_complete.html"
    success_url = reverse_lazy('accounts:customer_password_reset_complete')

class customer_password_doneView(PasswordResetDoneView):
    template_name = "accounts/customer_mail_sent_info.html"

class customer_password_reset_expireView(TemplateView):
    template_name = "accounts/customer_password_reset_expire.html"

class customer_password_resetView(PasswordResetConfirmView):
    template_name = "accounts/customer_password_reset.html"
    success_url = reverse_lazy('accounts:customer_password_reset_complete')

class store_account_editView(TemplateView):
    template_name = "accounts/store_account_edit.html"

def is_store_user(user) -> bool:
    """
    店舗ユーザー判定：
    StoreAccount(Account) の多テーブル継承がある前提。
    """
    print("IS_STORE_USER CHECK FOR USER:", user)
    print("IS_AUTHENTICATED:", user.is_authenticated if user else "NO USER")
    if not user or not user.is_authenticated:
        return False

    # 多テーブル継承だと、親(Account)から子(StoreAccount)へは user.storeaccount で辿れる
    # 存在しない場合は例外になるので try/except で判定
    try:
        _ = user.storeaccount
        return True
    except StoreAccount.DoesNotExist:
        return False
    except Exception:
        # 万が一関連名が違う/設計が違う場合の保険
        return False


# --- 店舗ログイン ---
class store_loginView(LoginView):
    template_name = "accounts/store_login.html"

    def get_success_url(self):
        return reverse_lazy("stores:store_top")

    def dispatch(self, request, *args, **kwargs):
        # GETアクセス時、もし店舗以外（企業や顧客）がログイン済みなら強制ログアウトさせる（既存ロジックの継承）
        if request.user.is_authenticated and not is_store_user(request.user):
            logout(request)
        
        # 店舗ユーザーとしてログイン済みならトップへ飛ばす
        if is_store_user(request.user):
            return redirect(self.get_success_url())
            
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        # ★店舗ユーザー判定
        if not is_store_user(user):
            messages.error(self.request, "店舗アカウントではありません。店舗用のログインIDをご確認ください。")
            return self.form_invalid(form)

        # 「次回から自動的にログインする」の処理（remember）
        remember = self.request.POST.get('remember')
        if not remember:
            self.request.session.set_expiry(0) # ブラウザを閉じたら終了
        else:
            self.request.session.set_expiry(None) # デフォルト期間（2週間など）保持

        return super().form_valid(form)

# --- 店舗ログアウト ---
class store_logoutView(LogoutView):
    # ログアウト後に店舗ログイン画面へリダイレクト
    next_page = reverse_lazy("accounts:store_login")
    
    # Django 4.0であれば、リンク(GET)でのログアウトを許可するためにdispatchを微調整
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)
    


class store_registerView(TemplateView):
    template_name = "accounts/store_register.html"

class store_account_application_confirmView(TemplateView):
    template_name = "accounts/store_account_application_confirm.html"

class store_account_application_inputView(TemplateView):
    template_name = "accounts/store_account_application_input.html"

class store_account_application_messageView(TemplateView):
    template_name = "accounts/store_account_application_message.html"

class store_account_mail_sentView(TemplateView):
    template_name = "accounts/store_account_mail_sent.html"

class store_account_privacyView(TemplateView):
    template_name = "accounts/store_account_privacy.html"

class store_account_searchView(TemplateView):
    template_name = "accounts/store_account_search.html"

class store_account_staff_confirmView(TemplateView):
    template_name = "accounts/store_account_staff_confirm.html" 

class store_account_staff_inputView(TemplateView):
    template_name = "accounts/store_account_staff_input.html"

class customer_topView(TemplateView):
    template_name = "accounts/customer_top.html"

