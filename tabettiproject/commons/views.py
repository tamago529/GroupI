from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.base import TemplateView
from django.views import View
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth import login
from commons.models import Review
from commons.models import CustomerAccount, Gender, AccountType

# 1. 完了画面のクラス：成否ステータスを受け取れるように拡張
class customer_common_completeView(TemplateView):
    template_name = "commons/customer_common_complete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # URLパラメータからメッセージとステータス（success/error）を取得
        context['msg'] = self.request.GET.get('msg', '完了しました。')
        context['status'] = self.request.GET.get('status', 'success')
        return context

# 2. 確認と保存を行うメインのView
class customer_common_confirmView(View):
    def get(self, request, *args, **kwargs):
        return redirect('accounts:customer_top')

    def post(self, request, *args, **kwargs):
        # 確定ボタン（is_final=true）から来た場合
        if request.POST.get('is_final') == 'true':
            return self.handle_final_save(request)

        # 入力画面から来た場合：確認画面用のデータ作成
        display_data = []
        hidden_data = {}

        for key, value in request.POST.items():
            if key == 'csrfmiddlewaretoken': continue
            hidden_data[key] = value
            
        field_labels = {
            'username': 'ユーザー名', 'email': 'メールアドレス', 'password': 'パスワード',
            'nickname': 'ニックネーム', 'phone_number': '電話番号', 
            'gender': '性別', 'birth_date': '生年月日', 'age_group': '年代', 
            'address': '住所', 'title': 'タイトル'
        }

        for key, value in hidden_data.items():
            if key in ['agree', 'is_final', 'store_id', 'review_id', 'birth_date_year', 'birth_date_month', 'birth_date_day']: continue
            label = field_labels.get(key, key)
            display_val = value
            if key == 'password': display_val = '********'
            
            if key == 'gender' and value:
                try:
                    from .models import Gender 
                    gender_obj = Gender.objects.get(id=value)
                    display_val = gender_obj.gender
                except: pass

            if key == 'age_group' and value:
                try:
                    from .models import AgeGroup
                    ag_obj = AgeGroup.objects.get(id=value)
                    display_val = ag_obj.age_range
                except: pass

            display_data.append((label, display_val, key in ['comment', 'address']))

        # 生年月日の集約表示
        b_year = hidden_data.get('birth_date_year')
        b_month = hidden_data.get('birth_date_month')
        b_day = hidden_data.get('birth_date_day')
        if b_year and b_month and b_day:
            display_data.append(('生年月日', f"{b_year}年{b_month}月{b_day}日", False))
            hidden_data['birth_date'] = f"{b_year}-{b_month}-{b_day}"

        hidden_data['is_final'] = 'true'

        context = {
            'mode_label': 'ご入力内容',
            'display_data': display_data,
            'hidden_data': hidden_data,
            'action_type': 'update',
            'submit_url': reverse('commons:customer_common_confirm')
        }
        return render(request, "commons/customer_common_confirm.html", context)

    def handle_final_save(self, request):
        """DB保存の実行と成否判定"""
        p = request.POST
        status = 'success'
        
        try:
            # 顧客タイプの取得
            from .models import AccountType, CustomerAccount # 適宜インポート
            acc_type, _ = AccountType.objects.get_or_create(account_type="顧客")

            # ユーザー作成の実行
            # 生年月日の再構築
            b_date = p.get('birth_date')
            if not b_date:
                b_year = p.get('birth_date_year')
                b_month = p.get('birth_date_month')
                b_day = p.get('birth_date_day')
                if b_year and b_month and b_day:
                    b_date = f"{b_year}-{b_month}-{b_day}"

            # ユーザー作成の実行
            new_user = CustomerAccount.objects.create_user(
                username=p.get('username'), 
                email=p.get('email'),
                password=p.get('password'),
                nickname=p.get('nickname', '新規ユーザー'),
                phone_number=p.get('phone_number', ''),
                birth_date=b_date,
                gender_id=p.get('gender') if p.get('gender') else None,
                age_group_id=p.get('age_group') if p.get('age_group') else None,
                address=p.get('address', ''),
                title=p.get('title', ''),
                account_type=acc_type
            )
            
            new_user.sub_email = p.get('email')
            new_user.save()
            
            # ログイン処理
            login(request, new_user)
            msg = "会員登録が完了しました！"

        except Exception as e:
            # 保存失敗時の処理
            status = 'error'
            msg = f"保存ができませんでした。恐れ入りますが、最初からやり直してください。（エラー内容: {str(e)}）"

        # 成否ステータスをパラメータに含めてリダイレクト
        params = urlencode({'msg': msg, 'status': status})
        return redirect(f"{reverse('commons:customer_common_complete')}?{params}")

class errorView(TemplateView):
    template_name = "commons/error.html"


class store_common_confirmView(TemplateView):
    template_name = "commons/store_common_confirm.html"


class store_common_completeView(TemplateView):
    template_name = "commons/store_common_complete.html"


class company_common_confirmView(TemplateView):
    template_name = "commons/company_common_confirm.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 🌟 HTMLの変数 {{ confirm_message }} に合わせて「confirm_message」で受け取る
        context['confirm_message'] = self.request.GET.get('confirm_message', '実行してよろしいですか？')
        
        # 🌟 OKボタンの飛び先
        context['next_url'] = self.request.GET.get('next_url', '#')

        # 🌟 キャンセル時の戻り先（方法3：自動で前の画面へ）
        referer = self.request.META.get('HTTP_REFERER')
        context['cancel_url'] = referer if referer else '/accounts/company_top/'
        
        return context


class company_common_completeView(TemplateView):
    template_name = "commons/company_common_complete.html"

    


# ✅ 口コミ削除フロー
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
        review.delete() 

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