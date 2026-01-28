"""
Imagen views for HTMX-powered image generation UI.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from blog.models import Image, Post

from .tasks import generate_cover_image, generate_custom_image


@login_required
@staff_member_required
@require_POST
def generate_cover(request, post_pk):
    """Trigger cover image generation for a post."""
    post = get_object_or_404(Post, pk=post_pk, author=request.user)
    custom_prompt = request.POST.get('prompt', '').strip()

    # Queue the task
    task = generate_cover_image.delay(post.pk, custom_prompt or None)

    if request.htmx:
        return render(request, 'components/generation_started.html', {
            'post': post,
            'task_id': task.id,
        })

    return JsonResponse({
        'status': 'queued',
        'task_id': task.id,
        'post_id': post.pk,
    })


@login_required
@staff_member_required
@require_POST
def generate_custom(request):
    """Generate a custom image from a prompt."""
    prompt = request.POST.get('prompt', '').strip()
    aspect_ratio = request.POST.get('aspect_ratio', '16:9')

    if not prompt:
        if request.htmx:
            return render(request, 'components/generation_error.html', {
                'error': 'Prompt is required',
            })
        return JsonResponse({'error': 'Prompt is required'}, status=400)

    # Queue the task
    task = generate_custom_image.delay(prompt, aspect_ratio)

    if request.htmx:
        return render(request, 'components/generation_started.html', {
            'task_id': task.id,
            'prompt': prompt,
        })

    return JsonResponse({
        'status': 'queued',
        'task_id': task.id,
    })


@login_required
@staff_member_required
def check_task(request, task_id):
    """Check the status of a generation task."""
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    status = {
        'task_id': task_id,
        'status': result.status,
        'ready': result.ready(),
    }

    if result.ready():
        if result.successful():
            image_id = result.result
            if image_id:
                try:
                    image = Image.objects.get(pk=image_id)
                    status['image_id'] = image_id
                    status['image_url'] = image.file.url
                except Image.DoesNotExist:
                    status['error'] = 'Image not found'
        elif result.failed():
            status['error'] = str(result.result)

    if request.htmx:
        return render(request, 'components/task_status.html', status)

    return JsonResponse(status)


@login_required
@staff_member_required
def generator_ui(request):
    """AI image generator interface."""
    return render(request, 'imagen/generator.html')
