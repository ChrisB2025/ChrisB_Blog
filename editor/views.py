"""
Editor views for HTMX-powered post editing.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from blog.models import Image, Post, PostStatus, Tag

from .forms import ImageUploadForm, PostForm


@login_required
@staff_member_required
def dashboard(request):
    """Editor dashboard with post list."""
    posts = Post.objects.filter(author=request.user).select_related('featured_image')
    drafts = posts.filter(status=PostStatus.DRAFT)
    published = posts.filter(status=PostStatus.PUBLISHED)

    return render(request, 'editor/dashboard.html', {
        'drafts': drafts,
        'published': published,
    })


@login_required
@staff_member_required
def post_create(request):
    """Create a new post."""
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()  # Save tags

            if request.htmx:
                return render(request, 'components/post_saved.html', {'post': post})
            return redirect('editor:post_edit', pk=post.pk)
    else:
        form = PostForm()

    return render(request, 'editor/post_form.html', {
        'form': form,
        'is_new': True,
    })


@login_required
@staff_member_required
def post_edit(request, pk):
    """Edit an existing post."""
    post = get_object_or_404(Post, pk=pk, author=request.user)

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save()

            if request.htmx:
                return render(request, 'components/post_saved.html', {'post': post})
            return redirect('editor:post_edit', pk=post.pk)
    else:
        form = PostForm(instance=post)

    return render(request, 'editor/post_form.html', {
        'form': form,
        'post': post,
        'is_new': False,
    })


@login_required
@staff_member_required
@require_POST
def post_preview(request):
    """Preview markdown content as HTML."""
    import markdown
    from django.conf import settings

    content_md = request.POST.get('content', '')
    md = markdown.Markdown(
        extensions=getattr(settings, 'MARKDOWN_EXTENSIONS', []),
        extension_configs=getattr(settings, 'MARKDOWN_EXTENSION_CONFIGS', {})
    )
    html = md.convert(content_md)

    return render(request, 'components/preview.html', {'content': html})


@login_required
@staff_member_required
@require_http_methods(['DELETE'])
def post_delete(request, pk):
    """Delete a post."""
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()

    if request.htmx:
        return render(request, 'components/post_deleted.html')
    return redirect('editor:dashboard')


@login_required
@staff_member_required
def image_manager(request):
    """Image management view."""
    images = Image.objects.all()

    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save()
            if request.htmx:
                return render(request, 'components/image_item.html', {'image': image})
            return redirect('editor:image_manager')
    else:
        form = ImageUploadForm()

    return render(request, 'editor/image_manager.html', {
        'images': images,
        'form': form,
    })


@login_required
@staff_member_required
@require_http_methods(['DELETE'])
def image_delete(request, pk):
    """Delete an image."""
    image = get_object_or_404(Image, pk=pk)
    image.file.delete()
    image.delete()

    if request.htmx:
        return JsonResponse({'status': 'deleted'})
    return redirect('editor:image_manager')


@login_required
@staff_member_required
def image_select(request, post_pk):
    """Select featured image for a post (HTMX modal)."""
    post = get_object_or_404(Post, pk=post_pk, author=request.user)
    images = Image.objects.all()

    if request.method == 'POST':
        image_id = request.POST.get('image_id')
        if image_id:
            image = get_object_or_404(Image, pk=image_id)
            post.featured_image = image
            post.save()

        if request.htmx:
            return render(request, 'components/featured_image.html', {'post': post})

    return render(request, 'components/image_select_modal.html', {
        'post': post,
        'images': images,
    })
