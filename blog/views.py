"""
Public blog views.
"""

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Comment, CommentStatus, Post, PostStatus, Tag


def home(request):
    """Home page with paginated post list."""
    posts = Post.objects.filter(
        status=PostStatus.PUBLISHED
    ).select_related('author', 'featured_image').prefetch_related('tags')

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # For HTMX requests, return just the post cards
    if request.htmx:
        return render(request, 'components/post_list.html', {'page_obj': page_obj})

    return render(request, 'blog/home.html', {'page_obj': page_obj})


def post_detail(request, slug):
    """Single post view."""
    post = get_object_or_404(
        Post.objects.select_related('author', 'featured_image').prefetch_related('tags'),
        slug=slug,
        status=PostStatus.PUBLISHED
    )

    # Get approved comments with threading
    comments = post.comments.filter(
        status=CommentStatus.APPROVED,
        parent__isnull=True
    ).prefetch_related('replies')

    # Get related posts (same tags)
    related_posts = Post.objects.filter(
        status=PostStatus.PUBLISHED,
        tags__in=post.tags.all()
    ).exclude(pk=post.pk).distinct()[:3]

    return render(request, 'blog/post_detail.html', {
        'post': post,
        'comments': comments,
        'related_posts': related_posts,
    })


def tag_list(request):
    """List all tags with post counts."""
    tags = Tag.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status=PostStatus.PUBLISHED))
    ).filter(post_count__gt=0).order_by('name')

    return render(request, 'blog/tag_list.html', {'tags': tags})


def tag_detail(request, slug):
    """Posts by tag."""
    tag = get_object_or_404(Tag, slug=slug)
    posts = Post.objects.filter(
        status=PostStatus.PUBLISHED,
        tags=tag
    ).select_related('author', 'featured_image').prefetch_related('tags')

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.htmx:
        return render(request, 'components/post_list.html', {'page_obj': page_obj})

    return render(request, 'blog/tag_detail.html', {
        'tag': tag,
        'page_obj': page_obj,
    })


def about(request):
    """About page."""
    return render(request, 'blog/about.html')


@require_GET
def search(request):
    """Search posts."""
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        # Use PostgreSQL full-text search if available
        try:
            search_vector = SearchVector('title', weight='A') + SearchVector('content_md', weight='B')
            search_query = SearchQuery(query)
            results = Post.objects.filter(
                status=PostStatus.PUBLISHED
            ).annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query)
            ).filter(search=search_query).order_by('-rank')[:20]
        except Exception:
            # Fallback to simple search for SQLite
            results = Post.objects.filter(
                status=PostStatus.PUBLISHED
            ).filter(
                Q(title__icontains=query) | Q(content_md__icontains=query)
            )[:20]

    if request.htmx:
        return render(request, 'components/search_results.html', {
            'results': results,
            'query': query,
        })

    return render(request, 'blog/search.html', {
        'results': results,
        'query': query,
    })


@require_GET
def copy_link(request):
    """Endpoint for copy link button (returns success message)."""
    return JsonResponse({'status': 'copied'})
