"""
Context processors for the blog app.
"""

from django.db.models import Count, Q

from .models import Post, PostStatus, Tag


def sidebar_context(request):
    """Add sidebar data to all templates."""
    # Recent posts
    recent_posts = Post.objects.filter(
        status=PostStatus.PUBLISHED
    ).select_related('featured_image').only(
        'title', 'slug', 'published_at', 'featured_image'
    )[:5]

    # Tags with post counts
    tags = Tag.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status=PostStatus.PUBLISHED))
    ).filter(post_count__gt=0).order_by('-post_count')[:15]

    return {
        'sidebar_recent_posts': recent_posts,
        'sidebar_tags': tags,
    }
