from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login ,logout
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView

from commons.models import StoreAccount,Account

#共通機能の定義

class company_account_managementView(TemplateView):
    template_name = "accounts/company_account_management.html"

class company_loginView(TemplateView):
    template_name = "accounts/company_login.html"

class company_logoutView(TemplateView):
    template_name = "accounts/company_logout.html" 

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
