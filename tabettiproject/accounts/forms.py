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


class CustomerRegisterForm(forms.ModelForm):
    # パスワード確認用フィールド
    password = forms.CharField(
        label="パスワード",
        widget=forms.PasswordInput(),
        min_length=8,
        help_text="8文字以上で入力してください。"
    )
    confirm_password = forms.CharField(
        label="パスワード（確認）",
        widget=forms.PasswordInput()
    )

    class Meta:
        model = Account  # いったんAccountベースで受けるか、CustomerAccountにするか。CustomerAccountはAccountを継承している。
        # DjangoのModelFormは継承モデルも扱えるが、AbstractUser継承のフィールドと自モデルのフィールドをどう扱うか。
        # ここでは直接 CustomerAccount を指定する。
        from commons.models import CustomerAccount
        model = CustomerAccount
        fields = [
            'email', 'password', 'nickname', 'phone_number', 
            'age_group', 'gender', 'address', 'title', 'location', 'birth_date'
        ]
        # sub_email は email をコピーして使う方針で除外、あるいは入力させるか。
        # fields にないものは save 時に手動で入れる必要がある。
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 必須属性の追加やclassの付与
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control' # CSSクラスが必要なら
            field.widget.attrs['placeholder'] = field.label

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            self.add_error('confirm_password', "パスワードが一致しません。")
        
        return cleaned_data

    def save(self, commit=True):
        # 親クラスのsaveを呼ぶ前に、パスワードのハッシュ化などが必要だが、
        # AbstractUserのモデルフォームを使わない場合、set_passwordを自分で呼ぶ必要がある。
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.username = user.email # usernameをemailと同じにする
        user.sub_email = user.email # sub_emailもemailと同じにする
        
        # AccountTypeを「顧客」に設定
        from commons.models import AccountType
        try:
            user.account_type = AccountType.objects.get(account_type="顧客")
        except AccountType.DoesNotExist:
            raise forms.ValidationError("アカウント種類マスタに'顧客'が存在しません。")

        if commit:
            user.save()
        return user
