import os
import django
import sys

# Windows環境での文字化け・エンコードエラー対策
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tabettiproject.settings')
django.setup()

from commons.models import Store
from django.db.models import Q

def delete_stores_without_coordinates():
    # 緯度または経度がNULLの店舗を検索
    stores_to_delete = Store.objects.filter(Q(latitude__isnull=True) | Q(longitude__isnull=True))
    count = stores_to_delete.count()
    
    print(f"座標が未登録の店舗数: {count}")
    
    if count > 0:
        # 削除実行
        deleted_count, _ = stores_to_delete.delete()
        print(f"{deleted_count} 件の店舗データを削除しました。")
    else:
        print("削除対象の店舗はありませんでした。")

if __name__ == "__main__":
    delete_stores_without_coordinates()
