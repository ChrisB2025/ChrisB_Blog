"""
Blog models: Post, Tag, Comment, Image, Profile.
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

import bleach
import markdown


class Profile(models.Model):
    """Extended user profile."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class Tag(models.Model):
    """Blog post tags (no categories per requirement)."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    wp_term_id = models.PositiveIntegerField(null=True, blank=True, help_text="Original WordPress term ID")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:tag_detail', kwargs={'slug': self.slug})


class Image(models.Model):
    """Uploaded images for blog posts."""
    file = models.ImageField(upload_to='images/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)
    caption = models.TextField(blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    size_bytes = models.PositiveIntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    ai_generated = models.BooleanField(default=False)
    ai_prompt = models.TextField(blank=True, help_text="Prompt used for AI generation")

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.original_name or self.file.name

    def save(self, *args, **kwargs):
        if self.file:
            if not self.original_name:
                self.original_name = self.file.name
            # Get image dimensions
            try:
                from PIL import Image as PILImage
                img = PILImage.open(self.file)
                self.width, self.height = img.size
            except Exception:
                pass
            # Get file size
            try:
                self.size_bytes = self.file.size
            except Exception:
                pass
        super().save(*args, **kwargs)


class PostStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    SCHEDULED = 'scheduled', 'Scheduled'
    PUBLISHED = 'published', 'Published'


class Post(models.Model):
    """Blog post."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    content_md = models.TextField(help_text="Content in Markdown format")
    content_html = models.TextField(blank=True, editable=False, help_text="Rendered HTML content")
    excerpt = models.TextField(blank=True, help_text="Short summary for previews")
    status = models.CharField(
        max_length=20,
        choices=PostStatus.choices,
        default=PostStatus.DRAFT
    )
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='posts')
    featured_image = models.ForeignKey(
        Image,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='featured_posts'
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    wp_post_id = models.PositiveIntegerField(null=True, blank=True, help_text="Original WordPress post ID")

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Generate slug if not provided
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure uniqueness
            base_slug = self.slug
            counter = 1
            while Post.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        # Convert Markdown to HTML
        self.content_html = self._render_markdown()

        # Set published_at when publishing
        if self.status == PostStatus.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def _render_markdown(self):
        """Render markdown content to sanitized HTML."""
        md = markdown.Markdown(
            extensions=getattr(settings, 'MARKDOWN_EXTENSIONS', []),
            extension_configs=getattr(settings, 'MARKDOWN_EXTENSION_CONFIGS', {})
        )
        html = md.convert(self.content_md)
        # Sanitize HTML
        allowed_tags = [
            'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'strong', 'em', 'u', 's', 'blockquote', 'code', 'pre',
            'ul', 'ol', 'li', 'a', 'img', 'table', 'thead', 'tbody',
            'tr', 'th', 'td', 'div', 'span', 'hr',
            'sup', 'sub',  # For footnotes
        ]
        allowed_attrs = {
            'a': ['href', 'title', 'target', 'rel'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            'code': ['class'],
            'pre': ['class'],
            'div': ['class'],
            'span': ['class'],
            'th': ['colspan', 'rowspan'],
            'td': ['colspan', 'rowspan'],
        }
        return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs)

    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})

    @property
    def is_published(self):
        return self.status == PostStatus.PUBLISHED and self.published_at and self.published_at <= timezone.now()

    @property
    def first_image_url(self):
        """Extract first image URL from content for thumbnail display.

        Converts local /uploads/ URLs to WordPress URLs since local files
        don't persist on Railway's ephemeral filesystem.
        """
        import re

        def to_wordpress_url(url):
            """Convert local /uploads/ URL to WordPress URL."""
            if not url:
                return None
            # Already a full URL (WordPress or other external)
            if url.startswith('http'):
                # Fix corrupted URLs with repeated WordPress prefixes
                if 'wordpress.com' in url:
                    # Extract the final valid path
                    match = re.search(r'/uploads/(?:images/)?(\d{4}/\d{2}/[^)\s"\'<>]+)$', url)
                    if match:
                        return f'https://chrisblanduk.wordpress.com/wp-content/uploads/{match.group(1)}'
                return url
            # Convert local /uploads/YYYY/MM/file or /uploads/images/YYYY/MM/file
            match = re.match(r'/uploads/(?:images/)?(\d{4}/\d{2}/.+)', url)
            if match:
                return f'https://chrisblanduk.wordpress.com/wp-content/uploads/{match.group(1)}'
            return url if not url.startswith('/uploads/') else None

        # Try HTML content first - find first image
        html_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        match = re.search(html_pattern, self.content_html or '')
        if match:
            return to_wordpress_url(match.group(1))

        # Fall back to markdown - find first image
        md_pattern = r'!\[[^\]]*\]\(([^)]+)\)'
        match = re.search(md_pattern, self.content_md or '')
        if match:
            return to_wordpress_url(match.group(1))

        return None

    @property
    def thumbnail_url(self):
        """Get thumbnail URL from post content."""
        return self.first_image_url

    @property
    def thumbnail_in_content(self):
        """Check if thumbnail URL is already present in content_html."""
        if not self.thumbnail_url or not self.content_html:
            return False
        return self.thumbnail_url in self.content_html

    @property
    def plain_excerpt(self):
        """Get plain text excerpt without markdown/HTML formatting."""
        import re
        from django.utils.html import strip_tags

        # Use excerpt if available
        if self.excerpt:
            return self.excerpt

        # Otherwise extract from content_html (strip HTML tags)
        if self.content_html:
            text = strip_tags(self.content_html)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        # Fall back to content_md with markdown stripped
        if self.content_md:
            text = self.content_md
            # Remove images
            text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
            # Remove links but keep text
            text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
            # Remove headers
            text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
            # Remove bold/italic
            text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        return ''


class CommentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    SPAM = 'spam', 'Spam'


class Comment(models.Model):
    """Comments on blog posts (migrated from WordPress)."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    author_name = models.CharField(max_length=100)
    author_email = models.EmailField()
    content = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=CommentStatus.choices,
        default=CommentStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    wp_comment_id = models.PositiveIntegerField(null=True, blank=True, help_text="Original WordPress comment ID")

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author_name} on {self.post.title}"

    @property
    def is_approved(self):
        return self.status == CommentStatus.APPROVED
