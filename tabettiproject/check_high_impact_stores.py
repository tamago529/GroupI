import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tabettiproject.settings')
django.setup()
from commons.models import Store, Review
from django.db.models import Avg, Sum, Max

# いいね数が多い順に店舗を調査
top_liked_reviews = Review.objects.order_by('-like_count')[:10]
for r in top_liked_reviews:
    s = r.store
    reviews = s.review_set.all()
    simple_avg = reviews.aggregate(Avg('score'))['score__avg']
    weighted_ctx = s.get_weighted_rating_context()
    print(f"Store: {s.store_name} (ID: {s.id})")
    print(f"  Simple Avg: {simple_avg:.2f}, Weighted Avg: {weighted_ctx['avg_rating']:.2f}, Count: {reviews.count()}")
    for rev in reviews:
        print(f"    Score: {rev.score}, Likes: {rev.like_count}, Trust: {rev.reviewer.trust_score}")
    print("-" * 20)
