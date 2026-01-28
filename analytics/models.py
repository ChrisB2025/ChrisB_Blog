"""
Analytics models for tracking page views.
"""

from django.db import models


class PageView(models.Model):
    """Simple page view tracking."""
    post = models.ForeignKey(
        'blog.Post',
        on_delete=models.CASCADE,
        related_name='page_views'
    )
    viewed_at = models.DateTimeField(auto_now_add=True)
    referrer = models.URLField(max_length=500, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True, help_text="Hashed IP for deduplication")

    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['post', 'viewed_at']),
            models.Index(fields=['viewed_at']),
        ]

    def __str__(self):
        return f"View of {self.post.title} at {self.viewed_at}"
