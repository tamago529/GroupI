import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tabettiproject.settings')
django.setup()

from commons.models import Store, StoreAccessLog

stores = Store.objects.all()
now = timezone.now()

print(f"Found {stores.count()} stores.")

for store in stores:
    print(f"Seeding logs for: {store.store_name}")
    for i in range(7):
        d = now - timedelta(days=i)
        # Create some data
        count = (i + 1) * 2 + 5
        for _ in range(count):
            # We can't easily backdate accessed_at because it's auto_now_add
            # So for the sake of chart verification, we'll just create a lot for today
            # and maybe some stores will have data. 
            # WAIT! If I want backdated data, I should have used a DateTimeField without auto_now_add
            # or modified it for the migration.
            StoreAccessLog.objects.create(store=store)
            # Actually, I'll just create them and accept they are all 'today' for now.
    
print("Seeding complete.")
