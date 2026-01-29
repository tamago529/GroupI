from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from commons.models import Review, CustomerAccount


@receiver(post_save, sender=Review)
def update_reviewer_trust_score_on_review_save(sender, instance, created, **kwargs):
    """
    レビュー投稿時に投稿者の信頼度スコアを更新
    """
    if instance.reviewer:
        # review_count と total_likes を更新
        reviews = Review.objects.filter(reviewer=instance.reviewer)
        instance.reviewer.review_count = reviews.count()
        instance.reviewer.total_likes = sum(r.like_count for r in reviews)
        instance.reviewer.save(update_fields=['review_count', 'total_likes'])
        
        # 信頼度スコアを更新
        instance.reviewer.update_trust_score()


@receiver(post_delete, sender=Review)
def update_reviewer_trust_score_on_review_delete(sender, instance, **kwargs):
    """
    レビュー削除時に投稿者の信頼度スコアを更新
    """
    if instance.reviewer:
        # review_count と total_likes を更新
        reviews = Review.objects.filter(reviewer=instance.reviewer)
        instance.reviewer.review_count = reviews.count()
        instance.reviewer.total_likes = sum(r.like_count for r in reviews)
        instance.reviewer.save(update_fields=['review_count', 'total_likes'])
        
        # 信頼度スコアを更新
        instance.reviewer.update_trust_score()
