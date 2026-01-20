from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from commons.models import Account

class CustomerLoginForm(AuthenticationForm):
    # HTMLの name="username" にあたる部分を「メールアドレス」として定義
    username = forms.EmailField(label="メールアドレス")

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            # データベースからメールアドレスでユーザーを探して認証
            try:
                user_obj = Account.objects.get(email=email)
                # パスワードの照合
                self.user_cache = authenticate(self.request, username=user_obj.username, password=password)
            except Account.DoesNotExist:
                self.user_cache = None

            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data