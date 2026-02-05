import os
import django
import sys

# Windows環境での文字化け・エンコードエラー対策
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tabettiproject.settings')
django.setup()

from commons.models import CustomerAccount, Review, Store
from django.db.models import Avg, Sum, Count, F

def check_trust_scores():
    customers = CustomerAccount.objects.all()
    print(f"Total customers: {customers.count()}")
    
    trust_scores = customers.values_list('trust_score', flat=True)
    if trust_scores:
        print(f"Trust score range: {min(trust_scores)} - {max(trust_scores)}")
        print(f"Average trust score: {sum(trust_scores)/len(trust_scores)}")
        
        counts = {}
        for s in trust_scores:
            counts[s] = counts.get(s, 0) + 1
        print("Trust score distribution (top 5):")
        for s, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {s}: {c} users")

    # Check some stores
    stores = Store.objects.annotate(
        simple_avg=Avg('review__score'),
        review_cnt=Count('review')
    ).filter(review_cnt__gt=0)[:5]
    
    print("\nStore Ratings comparison:")
    for s in stores:
        agg = Review.objects.filter(store=s).aggregate(
            weighted_sum=Sum(F("score") * F("reviewer__trust_score")),
            weight_total=Sum("reviewer__trust_score")
        )
        weighted_avg = agg['weighted_sum'] / agg['weight_total'] if agg['weight_total'] else 0
        print(f"Store: {s.store_name}")
        print(f"  Simple Avg: {s.simple_avg:.2f}")
        print(f"  Weighted Avg: {weighted_avg:.2f}")
        print(f"  Diff: {weighted_avg - (s.simple_avg or 0):.4f}")

if __name__ == "__main__":
    check_trust_scores()
