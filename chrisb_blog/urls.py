"""
URL configuration for chrisb_blog project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps import GenericSitemap
from django.contrib.sitemaps.views import sitemap
from django.http import JsonResponse
from django.urls import include, path

from blog.feeds import LatestPostsFeed
from blog.models import Post, PostStatus


def health_check(request):
    """Health check endpoint for Railway."""
    return JsonResponse({'status': 'ok'})

# Sitemap configuration
post_info = {
    'queryset': Post.objects.filter(status=PostStatus.PUBLISHED),
    'date_field': 'published_at',
}

sitemaps = {
    'posts': GenericSitemap(post_info, priority=0.6),
}

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('editor/', include('editor.urls')),
    path('imagen/', include('imagen.urls')),
    path('feed/', LatestPostsFeed(), name='rss_feed'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('', include('blog.urls')),
]

# Serve media files (needed for user uploads and AI-generated images)
# In production, consider using a CDN or cloud storage for better performance
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
