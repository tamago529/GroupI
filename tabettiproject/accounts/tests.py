from django.test import TestCase
from django.urls import reverse
from commons.models import AccountType, AgeGroup, Gender, CustomerAccount
from datetime import date

class CustomerRegisterTest(TestCase):
    def setUp(self):
        # マスタデータの作成
        self.account_type = AccountType.objects.create(account_type="顧客")
        self.age_group = AgeGroup.objects.create(age_range="20代")
        self.gender = Gender.objects.create(gender="男性")

    def test_get_register_page(self):
        """登録ページへのアクセス確認"""
        url = reverse('accounts:customer_register')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/customer_register.html')

    def test_post_register_success(self):
        """正常なデータでの登録確認"""
        url = reverse('accounts:customer_register')
        data = {
            'email': 'test@example.com',
            'password': 'Password123',
            'confirm_password': 'Password123',
            'nickname': 'テスト太郎',
            'phone_number': '090-1111-2222',
            'age_group': self.age_group.id,
            'gender': self.gender.id,
            'address': '東京都渋谷区',
            'title': 'こんにちは',
            'location': '渋谷',
            'birth_date': '1990-01-01',
        }
        response = self.client.post(url, data)
        
        # リダイレクト確認 (成功時は customer_top へ)
        self.assertRedirects(response, reverse('accounts:customer_top'))

        # データ作成確認
        self.assertTrue(CustomerAccount.objects.filter(email='test@example.com').exists())
        user = CustomerAccount.objects.get(email='test@example.com')
        self.assertEqual(user.username, 'test@example.com')
        self.assertEqual(user.account_type.account_type, '顧客')
        self.assertTrue(user.check_password('Password123'))
