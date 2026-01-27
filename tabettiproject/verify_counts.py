import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tabettiproject.settings')
django.setup()

from commons.models import StoreAccessLog, Store

print(f"Total Stores: {Store.objects.count()}")
print(f"Total Access Logs: {StoreAccessLog.objects.count()}")

# Check aggregation logic
from django.utils import timezone
from datetime import timedelta

today = timezone.now().date()
date_list = [today - timedelta(days=i) for i in range(6, -1, -1)]
print(f"Aggregation range: {date_list[0]} to {date_list[-1]}")

for d in date_list:
    count = StoreAccessLog.objects.filter(accessed_at__date=d).count()
    print(f"  {d}: {count}")

print("Verification complete.")
