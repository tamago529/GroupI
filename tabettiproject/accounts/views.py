from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout, login
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.db.models import Q
from django.views.generic import ListView, CreateView
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from commons.models import StoreAccount, Account
from .forms import CustomerLoginForm, CustomerRegisterForm
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)

# =========================
# 企業側
# =========================
class company_account_managementView(ListView):
    template_name = "accounts/company_account_management.html"
    model = Account
    context_object_name = "accounts"

    def get_queryset(self):
        queryset = super().get_queryset().select_related("account_type")

        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(username__icontains=q) |
                Q(email__icontains=q) |
                Q(customeraccount__nickname__icontains=q)
            )

        selected_type = self.request.GET.get("type", "all")
        if selected_type == "customer":
            queryset = queryset.filter(account_type__account_type="顧客")
        elif selected_type == "store":
            queryset = queryset.filter(account_type__account_type="店舗")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        context["selected_type"] = self.request.GET.get("type", "all")
        return context


class company_loginView(LoginView):
    template_name = "accounts/company_login.html"

    def get_success_url(self):
        return reverse_lazy("accounts:company_top")

    def form_valid(self, form):
        user = form.get_user()
        if user.account_type.account_type != "企業":
            messages.error(self.request, "運用管理アカウント以外はログインできません。")
            return self.form_invalid(form)
        return super().form_valid(form)


def company_logout_view(request):
    logout(request)
    return render(request, "accounts/company_logout.html")


class company_store_review_detailView(TemplateView):
    template_name = "accounts/company_store_review_detail.html"


class company_store_reviewView(TemplateView):
    template_name = "accounts/company_store_review.html"


class company_topView(TemplateView):
    template_name = "accounts/company_top.html"


# =========================
# 顧客側
# =========================
class customer_loginView(LoginView):
    template_name = "accounts/customer_login.html"
    authentication_form = CustomerLoginForm

    def get_success_url(self):
        return reverse_lazy("accounts:customer_top")

    def form_valid(self, form):
        user = form.get_user()
        try:
            _ = user.customeraccount
        except Exception:
            messages.error(self.request, "顧客アカウントではありません。")
            return self.form_invalid(form)
        return super().form_valid(form)


# --- 顧客ログアウト ---
def customer_logout_view(request):
    """
    ヘッダーのログアウトリンク（GET）から来ても、
    ログアウト後に customer_logout.html を表示する。
    """
    logout(request)
    return render(request, "accounts/customer_logout.html")


class customer_registerView(CreateView):
    template_name = "accounts/customer_register.html"
    form_class = CustomerRegisterForm
    success_url = reverse_lazy("accounts:customer_top")

    def form_valid(self, form):
        # フォームの保存（ユーザー作成）
        response = super().form_valid(form)
        # 作成したユーザーでログイン
        user = self.object
        login(self.request, user)
        return response


class customer_settingsView(TemplateView):
    template_name = "accounts/customer_settings.html"


class customermail_sendView(PasswordResetView):
    template_name = "accounts/customer_mail_send.html"
    email_template_name = "accounts/password_reset_email.html"
    success_url = reverse_lazy("accounts:customer_password_done")


class customer_password_reset_completeView(PasswordResetCompleteView):
    template_name = "accounts/customer_password_reset_complete.html"
    success_url = reverse_lazy("accounts:customer_password_reset_complete")


class customer_password_doneView(PasswordResetDoneView):
    template_name = "accounts/customer_mail_sent_info.html"


class customer_password_reset_expireView(TemplateView):
    template_name = "accounts/customer_password_reset_expire.html"


class customer_password_resetView(PasswordResetConfirmView):
    template_name = "accounts/customer_password_reset.html"
    success_url = reverse_lazy("accounts:customer_password_reset_complete")


# =========================
# 店舗側
# =========================
class store_account_editView(TemplateView):
    template_name = "accounts/store_account_edit.html"


def is_store_user(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    try:
        _ = user.storeaccount
        return True
    except StoreAccount.DoesNotExist:
        return False
    except Exception:
        return False


class store_loginView(LoginView):
    template_name = "accounts/store_login.html"

    def get_success_url(self):
        return reverse_lazy("stores:store_top")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not is_store_user(request.user):
            logout(request)
        if is_store_user(request.user):
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        if not is_store_user(user):
            messages.error(self.request, "店舗アカウントではありません。店舗用のログインIDをご確認ください。")
            return self.form_invalid(form)

        remember = self.request.POST.get("remember")
        if not remember:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(None)

        return super().form_valid(form)


# --- 店舗ログアウト（顧客側と同じロジック） ---
def store_logout_view(request):
    """
    ログアウト後に store_logout.html を表示する（顧客側と同じ）
    """
    logout(request)
    return render(request, "accounts/store_logout.html")



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
