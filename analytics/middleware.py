"""
Middleware for tracking page views.
"""

import hashlib


class PageViewMiddleware:
    """Track page views for blog posts."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Track views after successful response
        if (
            response.status_code == 200
            and hasattr(request, 'resolver_match')
            and request.resolver_match
            and request.resolver_match.url_name == 'post_detail'
            and request.resolver_match.namespace == 'blog'
        ):
            self._track_view(request)

        return response

    def _track_view(self, request):
        """Record a page view for the post."""
        from blog.models import Post
        from analytics.models import PageView

        slug = request.resolver_match.kwargs.get('slug')
        if not slug:
            return

        try:
            post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            return

        # Hash IP for privacy
        ip = self._get_client_ip(request)
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:32] if ip else ''

        PageView.objects.create(
            post=post,
            referrer=request.META.get('HTTP_REFERER', '')[:500],
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            ip_hash=ip_hash,
        )

    def _get_client_ip(self, request):
        """Get client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
