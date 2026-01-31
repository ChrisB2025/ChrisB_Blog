"""
Vertex AI Imagen 4 integration service.
"""

import base64
import io
import json
import logging
import os
from typing import Optional

from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def get_google_credentials():
    """Get Google Cloud credentials from environment variable or default."""
    credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')

    if credentials_json:
        from google.oauth2 import service_account
        credentials_info = json.loads(credentials_json)
        return service_account.Credentials.from_service_account_info(credentials_info)

    # Fall back to Application Default Credentials (for local dev)
    return None


class ImagenService:
    """Service for generating images using Google Vertex AI Imagen 4."""

    def __init__(self):
        self.project_id = settings.GOOGLE_CLOUD_PROJECT
        self.location = settings.VERTEX_AI_LOCATION
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Vertex AI client."""
        if self._client is None:
            try:
                import vertexai
                from vertexai.preview.vision_models import ImageGenerationModel

                credentials = get_google_credentials()
                vertexai.init(
                    project=self.project_id,
                    location=self.location,
                    credentials=credentials
                )
                self._client = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
            except Exception as e:
                logger.error(f"Failed to initialize Vertex AI client: {e}")
                raise

        return self._client

    def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        aspect_ratio: str = "16:9",
        number_of_images: int = 1,
    ) -> list[bytes]:
        """
        Generate images using Imagen 4.

        Args:
            prompt: Text prompt describing the desired image
            negative_prompt: Things to avoid in the image
            aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            number_of_images: Number of images to generate (1-4)

        Returns:
            List of image bytes
        """
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT not configured")

        try:
            response = self.client.generate_images(
                prompt=prompt,
                negative_prompt=negative_prompt,
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                safety_filter_level="block_few",
                person_generation="allow_adult",
            )

            images = []
            for image in response.images:
                images.append(image._image_bytes)

            return images

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise

    def generate_blog_cover(self, title: str, content_excerpt: str = "") -> bytes:
        """
        Generate a blog post cover image.

        Args:
            title: Blog post title
            content_excerpt: Optional excerpt for context

        Returns:
            Image bytes
        """
        # Create a prompt optimized for blog covers
        prompt = f"""
        Create a professional, modern blog header image for an article titled "{title}".
        Style: Clean, minimalist, professional photography or illustration.
        Theme: Technology, software development, digital innovation.
        Colors: Rich, sophisticated palette with good contrast.
        Composition: Suitable for a 16:9 header image with space for text overlay.
        {f'Context: {content_excerpt[:200]}' if content_excerpt else ''}
        """

        negative_prompt = "text, words, letters, watermark, logo, low quality, blurry, distorted"

        images = self.generate_image(
            prompt=prompt.strip(),
            negative_prompt=negative_prompt,
            aspect_ratio="16:9",
            number_of_images=1,
        )

        return images[0] if images else None


def create_image_from_bytes(image_bytes: bytes, filename: str, prompt: str = "") -> "Image":
    """
    Create an Image model instance from bytes.

    Args:
        image_bytes: Raw image bytes
        filename: Desired filename
        prompt: AI prompt used for generation

    Returns:
        Image model instance (unsaved)
    """
    from blog.models import Image

    content_file = ContentFile(image_bytes, name=filename)

    image = Image(
        file=content_file,
        original_name=filename,
        ai_generated=True,
        ai_prompt=prompt,
    )

    return image
