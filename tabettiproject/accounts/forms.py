from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import authenticate, get_user_model, login
from commons.models import Account, CustomerAccount, StoreAccount, AccountType
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives


class StoreLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(attrs={"autofocus": True})
    )

    def clean(self):
        email = (self.cleaned_data.get("username") or "").strip()
        password = self.cleaned_data.get("password") or ""

        if not email or not password:
            raise ValidationError("メールアドレスとパスワードを入力してください。")

        UserModel = get_user_model()

        user = (
            UserModel._default_manager
            .filter(email__iexact=email, is_active=True, storeaccount__isnull=False)
            .order_by("pk")
            .first()
        )
        if not user:
            raise ValidationError("メールアドレスまたはパスワードが正しくありません。")

        self.user_cache = authenticate(
            self.request,
            username=user.get_username(),
            password=password,
        )

        if self.user_cache is None:
            raise ValidationError("メールアドレスまたはパスワードが正しくありません。")

        self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

class CustomerPasswordResetForm(PasswordResetForm):
    """
    ✅ 同一メールが複数アカウントに存在しても、メール送信は 1通だけにする
    （customer_mail_send 用：顧客アカウントのみ対象）
    """
    def get_users(self, email):
        UserModel = get_user_model()
        email_field = UserModel.get_email_field_name()

        qs = UserModel._default_manager.filter(
            **{f"{email_field}__iexact": email},
            is_active=True,
        )

        # ✅ 顧客だけ（CustomerAccount のみ）
        qs = qs.filter(customeraccount__isnull=False)

        # ✅ 1人だけ返す（古い順/小さいPKを採用）
        user = qs.order_by("pk").first()
        if not user:
            return []
        return [user]    

class CustomerRegisterForm(forms.ModelForm):
    # パスワード確認用フィールド
    password = forms.CharField(
        label="パスワード",
        widget=forms.PasswordInput(),
        min_length=8,
        help_text="8文字以上で入力してください。"
    )
    # ユーザーネーム（ログインID）フィールドをカスタマイズ
    username = forms.CharField(
        label="ユーザーネーム",
        help_text="※ログイン時に使用するため、忘れないよう必ず保存してください。この項目は必須です。<br>半角アルファベット、半角数字、および記号（@/./+/-/_）のみ使用可能です（150文字以下）。"
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
            'email', 'username', 'password', 'nickname', 'phone_number', 
            'age_group', 'gender', 'address', 'title', 'birth_date'
        ]
        widgets = {
            'birth_date': forms.SelectDateWidget(
                years=range(1920, timezone.now().year + 1)
            ),
        }
        # sub_email は email をコピーして使う方針で除外、あるいは入力させるか。
        # fields にないものは save 時に手動で入れる必要がある。
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            from commons.models import Account
            if Account.objects.filter(email=email).exists():
                raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            from commons.models import Account
            if Account.objects.filter(username=username).exists():
                raise forms.ValidationError("このユーザーネームは既に使われています。")
        return username

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
        # user.username = user.email  # 👈 ここを削除：フォームの入力値をそのまま使う
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

class CustomerSettingsForm(forms.ModelForm):
    # Account(AbstractUser) のフィールド
    last_name = forms.CharField(label="姓", required=False)
    first_name = forms.CharField(label="名", required=False)
    email = forms.EmailField(label="メールアドレス", required=True)
    standard_score = forms.ChoiceField(
        label="標準点",
        choices=[(0, "未選択")] + [(i, f"{'★' * i}{'☆' * (5-i)} {i}") for i in range(5, 0, -1)],
        initial=0,
        required=False,
        widget=forms.Select(attrs={'class': 'rating-select'})
    )

    class Meta:
        from commons.models import CustomerAccount
        model = CustomerAccount
        fields = [
            'last_name_kana', 'first_name_kana', 'gender', 'phone_number',
            'nickname', 'occupation', 'camera', 'standard_score', 'introduction',
            'title', 'subtitle', 'genre_focus', 'icon_image', 'cover_image'
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            from commons.models import Account
            qs = Account.objects.filter(email=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 追加フィールドを任意にする（モデルの blank=True でも自動でなるが、念のため明示）
        optional_fields = [
            'last_name_kana', 'first_name_kana', 'occupation', 'camera', 
            'introduction', 'title', 'subtitle', 'genre_focus', 'phone_number'
        ]
        for field_name in optional_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False

        if self.instance and self.instance.pk:
            # Account のフィールドを初期値にセット
            self.fields['last_name'].initial = self.instance.last_name
            self.fields['first_name'].initial = self.instance.first_name
            self.fields['email'].initial = self.instance.email
        
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        user = super().save(commit=False)
        # Account のフィールドを更新
        user.last_name = self.cleaned_data['last_name']
        user.first_name = self.cleaned_data['first_name']
        user.email = self.cleaned_data['email']
        user.sub_email = user.email

        if commit:
            user.save()
        return user

class StorePasswordResetForm(PasswordResetForm):
    """
    店舗アカウントだけを対象にし、メール内リンクは店舗用confirmへ
    """
    def get_users(self, email):
        UserModel = get_user_model()
        email_field = UserModel.get_email_field_name()

        qs = UserModel._default_manager.filter(
            **{f"{email_field}__iexact": email},
            is_active=True,
        ).filter(storeaccount__isnull=False)

        user = qs.order_by("pk").first()
        return [user] if user else []


    def save(
        self,
        domain_override=None,
        subject_template_name="accounts/password_reset_subject.txt",
        email_template_name="accounts/store_password_reset_email.html",
        use_https=False,
        token_generator=default_token_generator,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        """
        ★ここが肝：
        Django標準は 'password_reset_confirm' 固定なので、
        店舗用URLを自前で作って context に reset_url を渡す。
        """
        if extra_email_context is None:
            extra_email_context = {}

        for user in self.get_users(self.cleaned_data["email"]):
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)

            # 店舗用confirm URL（あなたのURL名に合わせる）
            path = reverse("accounts:store_password_reset_confirm", kwargs={"uidb64": uid, "token": token})
            if request is not None:
                reset_url = request.build_absolute_uri(path)
            else:
                # requestが無い場合の保険（通常 permit からは request がある）
                protocol = "https" if use_https else "http"
                domain = domain_override or "127.0.0.1:8000"
                reset_url = f"{protocol}://{domain}{path}"

            context = {
                "email": user.email,
                "domain": domain_override or (request.get_host() if request else ""),
                "site_name": "タベッチ",
                "uid": uid,
                "user": user,
                "token": token,
                "protocol": "https" if use_https else "http",
                "reset_url": reset_url,
                **(extra_email_context or {}),
            }

            subject = render_to_string(subject_template_name, context).strip()
            body = render_to_string(email_template_name, context)

            msg = EmailMultiAlternatives(subject, body, from_email, [user.email])
            msg.send()

class CustomerLoginForm(AuthenticationForm):
    """
    顧客ログイン（ひとまず Django 標準の AuthenticationForm と同等）
    ＝username/password でログイン
    """
    username = forms.CharField(label="ユーザー名", widget=forms.TextInput(attrs={"autofocus": True}))

    def clean(self):
        # 標準の認証処理に任せる（authenticate呼び出し等は親がやる）
        return super().clean()

class StoreSetPasswordForm(SetPasswordForm):
    email = forms.EmailField(label="ログインID（メールアドレス）", required=True)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and self.user.email != email:
            raise ValidationError("メールアドレスが一致しません。")
        return email