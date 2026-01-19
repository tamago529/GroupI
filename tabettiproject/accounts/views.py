from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login ,logout
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView

from commons.models import StoreAccount,Account
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy, reverse # 追加
from django.contrib import messages                         # エラー表示用
from django.db.models import Q
from django.views.generic import ListView
#共通機能の定義

class company_account_managementView(ListView):
    template_name = "accounts/company_account_management.html"
    model = Account
    context_object_name = "accounts"

    def get_queryset(self):
        queryset = super().get_queryset().select_related('account_type')
        
        # 1. 検索ワード（ID、メアド、名前で検索）
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(username__icontains=q) | 
                Q(email__icontains=q) |
                Q(customeraccount__nickname__icontains=q)
            )

        # 2. アカウント種別絞り込み
        # チェックボックスの値（customer, store）を取得
        types = self.request.GET.getlist('type')
        if types:
            # AccountTypeマスタの名称で絞り込む（マスタの名称に合わせて調整してください）
            type_queries = Q()
            if 'customer' in types:
                type_queries |= Q(account_type__account_type='顧客')
            if 'store' in types:
                type_queries |= Q(account_type__account_type='店舗')
            queryset = queryset.filter(type_queries)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['selected_types'] = self.request.GET.getlist('type')
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

class customer_loginView(TemplateView):
    template_name = "accounts/customer_login.html"

class customer_logoutView(TemplateView):
    template_name = "accounts/customer_logout.html"

class customer_registerView(TemplateView):
    template_name = "accounts/customer_register.html"

class customer_settingsView(TemplateView):
    template_name = "accounts/customer_settings.html"

class customermail_sendView(TemplateView):
    template_name = "accounts/customer_mail_send.html"

class customer_password_reset_completeView(TemplateView):
    template_name = "accounts/customer_password_reset_complete.html"

class customer_password_reset_expireView(TemplateView):                    
    template_name = "accounts/customer_password_reset_expire.html"

class customer_password_resetView(TemplateView):
    template_name = "accounts/customer_password_reset.html"

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


@method_decorator(csrf_exempt, name="dispatch")
class store_loginView(TemplateView):
    template_name = "accounts/store_login.html"

    def get(self, request, *args, **kwargs):
        # すでにログインしていても「店舗ユーザーじゃない」なら一旦ログアウトして店舗ログイン画面へ
        if request.user.is_authenticated and not is_store_user(request.user):
            logout(request)

        # 店舗ユーザーでログイン済みなら店舗トップへ
        if is_store_user(request.user):
            return redirect("stores:store_top" )

        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        login_id = (request.POST.get("login_id") or "").strip()
        password = request.POST.get("password") or ""
        remember = request.POST.get("remember")  # checkbox
        print("login_id:", login_id, " password:", password, " remember:", remember)

        if not login_id or not password:
            messages.error(request, "ログインIDとパスワードを入力してください。")
            return render(request, self.template_name)
        
        user = Account.objects.filter(username=login_id).first()
        print("test_user:", user)
        print("RAW PASSWORD FIELD:", user.password)
        print("CHECK_PASSWORD:", user.check_password(password))

        # login_id を username として認証（Account(AbstractUser)のusername）
        # user = authenticate(request, username=login_id, password=password)
        # print("AUTHENTICATED USER:", user)
        if user is None:
            print("AUTHENTICATION FAILED")
            messages.error(request, "ログインIDまたはパスワードが正しくありません。")
            return render(request, self.template_name)

        # ★店舗ユーザー以外は店舗ログインとして通さない
        if not is_store_user(user):
            print("NOT A STORE USER")
            messages.error(request, "店舗アカウントではありません。店舗用のログインIDをご確認ください。")
            return render(request, self.template_name)

        login(request, user)

        # 自動ログイン未チェックならブラウザ終了でセッション破棄
        if not remember:
            request.session.set_expiry(0)

        return redirect("stores:store_top")



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
