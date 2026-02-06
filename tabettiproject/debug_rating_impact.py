import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tabettiproject.settings')
django.setup()
from commons.models import Store, Review
from django.db.models import Avg

s = Store.objects.filter(review__isnull=False).first()
if s:
    reviews = s.review_set.all()
    simple_avg = reviews.aggregate(Avg('score'))['score__avg']
    weighted_ctx = s.get_weighted_rating_context()
    print(f"Store: {s.store_name}")
    print(f"Simple Avg: {simple_avg}")
    print(f"Weighted Avg: {weighted_ctx['avg_rating']}")
    print("-" * 30)
    for r in reviews:
        trust = r.reviewer.trust_score
        likes = r.like_count
        weight = trust + (likes * 10)
        print(f"Score: {r.score}, Likes: {likes}, Trust: {trust}, CalcWeight: {weight:.2f}")
else:
    print("No store with reviews found.")
