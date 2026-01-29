from django.core.management.base import BaseCommand
from commons.models import CustomerAccount


class Command(BaseCommand):
    help = '全ユーザーの信頼度スコアを更新します'

    def handle(self, *args, **options):
        self.stdout.write('信頼度スコアの更新を開始します...')
        
        customers = CustomerAccount.objects.all()
        total = customers.count()
        updated = 0
        
        for customer in customers:
            try:
                customer.update_trust_score()
                updated += 1
                
                if updated % 100 == 0:
                    self.stdout.write(f'進捗: {updated}/{total}')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'ユーザー {customer.nickname} の更新に失敗: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'完了: {updated}/{total} 人のユーザーの信頼度スコアを更新しました')
        )
