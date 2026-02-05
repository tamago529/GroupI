import os
import django

# Django環境のセットアップ
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tabettiproject.settings')
django.setup()

from commons.models import CustomerAccount, Follow

def sync_data():
    print("Syncing follower_count for all customers...")
    customers = CustomerAccount.objects.all()
    count = 0
    for customer in customers:
        # フォロワー数をカウント
        f_count = Follow.objects.filter(followee=customer).count()
        customer.follower_count = f_count
        # trust_score を再計算して保存
        customer.update_trust_score()
        count += 1
        if count % 100 == 0:
            print(f"Processed {count} customers...")
    
    print(f"Successfully finished! Processed {count} customers.")

if __name__ == "__main__":
    sync_data()
