#!/usr/bin/env python
"""
Featured Image Extraction Script

Extracts the first image from post content and sets it as the featured image
for posts that don't already have one.

Usage:
    python scripts/extract_featured_images.py
"""

import hashlib
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chrisb_blog.settings')

import django
django.setup()

from django.conf import settings
from django.core.files.base import ContentFile

from blog.models import Image, Post


def extract_first_image_url(content: str) -> str | None:
    """Extract the first image URL from markdown/HTML content."""
    # HTML images: <img src="url">
    html_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    match = re.search(html_pattern, content)
    if match:
        return match.group(1)

    # Markdown images: ![alt](url)
    md_pattern = r'!\[[^\]]*\]\(([^)]+)\)'
    match = re.search(md_pattern, content)
    if match:
        return match.group(1)

    return None


def download_image(url: str) -> tuple[bytes, str] | None:
    """Download image from URL and return bytes and filename."""
    # Skip data URLs
    if url.startswith('data:'):
        return None

    # Handle relative URLs (assume local media)
    if url.startswith('/'):
        # Local file - read directly
        local_path = Path(settings.BASE_DIR) / url.lstrip('/')
        if local_path.exists():
            filename = local_path.name
            return local_path.read_bytes(), filename

        # Try media root
        media_path = Path(settings.MEDIA_ROOT) / url.replace(settings.MEDIA_URL, '').lstrip('/')
        if media_path.exists():
            filename = media_path.name
            return media_path.read_bytes(), filename

        return None

    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()

        # Get filename from URL
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename:
            # Generate filename from URL hash
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            content_type = response.headers.get('content-type', 'image/jpeg')
            ext = content_type.split('/')[-1].split(';')[0]
            filename = f"image-{url_hash}.{ext}"

        return response.content, filename

    except Exception as e:
        print(f"  Error downloading {url}: {e}")
        return None


def find_existing_image(url: str) -> Image | None:
    """Check if an image already exists for this URL."""
    # Extract filename from URL
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    if filename:
        # Check if an image with this filename exists
        existing = Image.objects.filter(original_name=filename).first()
        if existing:
            return existing
        # Also check by file path
        existing = Image.objects.filter(file__icontains=filename).first()
        if existing:
            return existing
    return None


def process_post(post: Post) -> bool:
    """Extract first image from post and set as featured image."""
    # Skip if already has featured image
    if post.featured_image:
        return False

    # Try content_html first (more likely to have images after WordPress import)
    image_url = extract_first_image_url(post.content_html)

    # Fall back to markdown content
    if not image_url:
        image_url = extract_first_image_url(post.content_md)

    if not image_url:
        return False

    print(f"  Found image: {image_url}")

    # Check if image already exists
    existing = find_existing_image(image_url)
    if existing:
        print(f"  Using existing image: {existing}")
        post.featured_image = existing
        post.save(update_fields=['featured_image'])
        return True

    # Download the image
    result = download_image(image_url)
    if result is None:
        return False

    image_bytes, filename = result

    # Create Image object
    content_file = ContentFile(image_bytes, name=filename)
    image = Image(
        file=content_file,
        original_name=filename,
        alt_text=f"Featured image for {post.title}",
    )
    image.save()

    # Set as featured image
    post.featured_image = image
    post.save(update_fields=['featured_image'])
    print(f"  Created featured image: {filename}")
    return True


def main():
    print("Extracting featured images from post content...")

    posts_without_featured = Post.objects.filter(featured_image__isnull=True)
    total = posts_without_featured.count()

    print(f"Found {total} posts without featured images")

    updated = 0
    for post in posts_without_featured:
        print(f"\nProcessing: {post.title}")
        if process_post(post):
            updated += 1
        else:
            print("  No image found or could not download")

    print(f"\n\nComplete! Set featured images for {updated} posts.")
    return updated


if __name__ == '__main__':
    main()
