import os
import django
import requests
import time
import sys

# Windows環境での文字化け・エンコードエラー対策
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tabettiproject.settings')
django.setup()

from commons.models import Store

def update_coordinates():
    stores = Store.objects.filter(latitude__isnull=True)
    count = stores.count()
    print(f"Updating coordinates for {count} stores...")

    for i, store in enumerate(stores):
        address = store.address
        if not address:
            # print(f"Skipping {store.store_name} (No address)")
            continue

        try:
            url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={address}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    coords = data[0]['geometry']['coordinates']
                    store.longitude = coords[0]
                    store.latitude = coords[1]
                    store.save()
                    print(f"[{i+1}/{count}] Updated {store.store_name}: {store.latitude}, {store.longitude}")
                else:
                    print(f"[{i+1}/{count}] Not found: {store.store_name} ({address})")
            else:
                print(f"[{i+1}/{count}] Error fetching {store.store_name}: Status {response.status_code}")
            
            # API負荷軽減
            time.sleep(0.1)

        except Exception as e:
            try:
                print(f"Error processing {store.store_name}: {e}")
            except:
                print(f"Error processing a store: {e}")

    print("Store coordinate update completed.")

if __name__ == "__main__":
    update_coordinates()

if __name__ == "__main__":
    update_coordinates()
