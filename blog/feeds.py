"""
RSS feed for blog posts.
"""

from django.contrib.syndication.views import Feed
from django.urls import reverse

from .models import Post, PostStatus


class LatestPostsFeed(Feed):
    title = "ChrisB Blog"
    link = "/"
    description = "Latest posts from ChrisB Blog"

    def items(self):
        return Post.objects.filter(
            status=PostStatus.PUBLISHED
        ).order_by('-published_at')[:10]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or item.content_html[:500]

    def item_link(self, item):
        return item.get_absolute_url()

    def item_pubdate(self, item):
        return item.published_at

    def item_author_name(self, item):
        return item.author.get_full_name() or item.author.username
