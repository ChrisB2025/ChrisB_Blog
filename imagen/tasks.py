"""
Celery tasks for async image generation.
"""

import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_cover_image(self, post_id: int, custom_prompt: str = None):
    """
    Generate a cover image for a blog post asynchronously.

    Args:
        post_id: ID of the Post to generate cover for
        custom_prompt: Optional custom prompt (uses title if not provided)
    """
    from blog.models import Post
    from imagen.services import ImagenService, create_image_from_bytes

    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        logger.error(f"Post {post_id} not found")
        return

    prompt = custom_prompt or post.title
    excerpt = post.excerpt or post.content_md[:500]

    try:
        service = ImagenService()
        image_bytes = service.generate_blog_cover(prompt, excerpt)

        if image_bytes:
            filename = f"cover-{post.slug}-{uuid.uuid4().hex[:8]}.png"
            image = create_image_from_bytes(
                image_bytes,
                filename,
                prompt=f"Blog cover for: {prompt}"
            )
            image.save()

            # Set as featured image
            post.featured_image = image
            post.save(update_fields=['featured_image'])

            logger.info(f"Generated cover image for post {post_id}: {image.pk}")
            return image.pk

    except Exception as e:
        logger.error(f"Failed to generate cover for post {post_id}: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_custom_image(self, prompt: str, aspect_ratio: str = "16:9"):
    """
    Generate a custom image from a prompt.

    Args:
        prompt: Text prompt for image generation
        aspect_ratio: Desired aspect ratio

    Returns:
        Image ID if successful
    """
    from imagen.services import ImagenService, create_image_from_bytes

    try:
        service = ImagenService()
        images = service.generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            number_of_images=1,
        )

        if images:
            filename = f"generated-{uuid.uuid4().hex[:8]}.png"
            image = create_image_from_bytes(images[0], filename, prompt=prompt)
            image.save()

            logger.info(f"Generated custom image: {image.pk}")
            return image.pk

    except Exception as e:
        logger.error(f"Failed to generate custom image: {e}")
        raise self.retry(exc=e, countdown=60)
