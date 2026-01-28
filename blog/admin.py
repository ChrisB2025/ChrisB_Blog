"""
Django admin configuration for blog models.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Comment, Image, Post, Profile, Tag


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio_preview')
    search_fields = ('user__username', 'user__email', 'bio')

    def bio_preview(self, obj):
        return obj.bio[:50] + '...' if len(obj.bio) > 50 else obj.bio
    bio_preview.short_description = 'Bio'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'post_count', 'wp_term_id')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

    def post_count(self, obj):
        return obj.posts.count()
    post_count.short_description = 'Posts'


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('thumbnail', 'original_name', 'dimensions', 'size_display', 'ai_generated', 'uploaded_at')
    list_filter = ('ai_generated', 'uploaded_at')
    search_fields = ('original_name', 'alt_text', 'caption')
    readonly_fields = ('width', 'height', 'size_bytes', 'uploaded_at')

    def thumbnail(self, obj):
        if obj.file:
            return format_html('<img src="{}" style="max-width:100px;max-height:100px;"/>', obj.file.url)
        return '-'
    thumbnail.short_description = 'Preview'

    def dimensions(self, obj):
        if obj.width and obj.height:
            return f'{obj.width}x{obj.height}'
        return '-'
    dimensions.short_description = 'Size'

    def size_display(self, obj):
        if obj.size_bytes:
            if obj.size_bytes < 1024:
                return f'{obj.size_bytes} B'
            elif obj.size_bytes < 1024 * 1024:
                return f'{obj.size_bytes / 1024:.1f} KB'
            else:
                return f'{obj.size_bytes / (1024 * 1024):.1f} MB'
        return '-'
    size_display.short_description = 'File Size'


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ('author_name', 'author_email', 'content', 'status', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'published_at', 'tag_list', 'comment_count')
    list_filter = ('status', 'author', 'tags', 'created_at')
    search_fields = ('title', 'slug', 'content_md', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    date_hierarchy = 'published_at'
    inlines = [CommentInline]

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'status')
        }),
        ('Content', {
            'fields': ('content_md', 'excerpt', 'featured_image')
        }),
        ('Categorization', {
            'fields': ('tags',)
        }),
        ('Dates', {
            'fields': ('published_at',),
            'classes': ('collapse',)
        }),
        ('WordPress Import', {
            'fields': ('wp_post_id',),
            'classes': ('collapse',)
        }),
    )

    def tag_list(self, obj):
        return ', '.join([tag.name for tag in obj.tags.all()[:3]])
    tag_list.short_description = 'Tags'

    def comment_count(self, obj):
        return obj.comments.count()
    comment_count.short_description = 'Comments'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'post', 'status', 'created_at', 'content_preview')
    list_filter = ('status', 'created_at')
    search_fields = ('author_name', 'author_email', 'content')
    actions = ['approve_comments', 'mark_as_spam']

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'

    @admin.action(description='Approve selected comments')
    def approve_comments(self, request, queryset):
        queryset.update(status='approved')

    @admin.action(description='Mark selected as spam')
    def mark_as_spam(self, request, queryset):
        queryset.update(status='spam')
