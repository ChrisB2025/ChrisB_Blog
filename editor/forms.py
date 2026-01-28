"""
Forms for the editor app.
"""

from django import forms

from blog.models import Image, Post


class PostForm(forms.ModelForm):
    """Form for creating/editing posts."""

    class Meta:
        model = Post
        fields = ['title', 'slug', 'content_md', 'excerpt', 'status', 'tags', 'featured_image', 'published_at']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Post title',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'url-slug',
            }),
            'content_md': forms.Textarea(attrs={
                'class': 'form-textarea markdown-editor',
                'rows': 20,
                'placeholder': 'Write your content in Markdown...',
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Brief summary for previews...',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
            'tags': forms.CheckboxSelectMultiple(attrs={
                'class': 'tag-checkbox',
            }),
            'published_at': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local',
            }),
        }


class ImageUploadForm(forms.ModelForm):
    """Form for uploading images."""

    class Meta:
        model = Image
        fields = ['file', 'alt_text', 'caption']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*',
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Alt text for accessibility',
            }),
            'caption': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Optional caption',
            }),
        }
