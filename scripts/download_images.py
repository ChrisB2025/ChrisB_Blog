#!/usr/bin/env python
"""
WordPress Image Download Script

Downloads images from WordPress posts and updates the references.

Usage:
    python scripts/download_images.py <wordpress-domain>

Example:
    python scripts/download_images.py chrisblanduk.com
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


def extract_image_urls(content: str, domain: str) -> list[str]:
    """Extract image URLs from markdown/HTML content."""
    urls = set()

    # Markdown images: ![alt](url)
    md_pattern = r'!\[[^\]]*\]\(([^)]+)\)'
    for match in re.finditer(md_pattern, content):
        url = match.group(1)
        if domain in url or url.startswith('/'):
            urls.add(url)

    # HTML images: <img src="url">
    html_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    for match in re.finditer(html_pattern, content):
        url = match.group(1)
        if domain in url or url.startswith('/'):
            urls.add(url)

    return list(urls)


def download_image(url: str, base_url: str) -> tuple[bytes, str] | None:
    """Download image from URL and return bytes and filename."""
    # Handle relative URLs
    if url.startswith('/'):
        url = urljoin(base_url, url)

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


def process_post_images(post: Post, domain: str, base_url: str) -> int:
    """Download images from a post and update references."""
    downloaded = 0
    new_content = post.content_md

    # Extract image URLs
    image_urls = extract_image_urls(post.content_md, domain)

    for url in image_urls:
        result = download_image(url, base_url)
        if result is None:
            continue

        image_bytes, filename = result

        # Create Image object
        content_file = ContentFile(image_bytes, name=filename)
        image = Image(
            file=content_file,
            original_name=filename,
            alt_text=f"Image from {post.title}",
        )
        image.save()

        # Update content with new URL
        new_url = image.file.url
        new_content = new_content.replace(url, new_url)
        downloaded += 1
        print(f"  Downloaded: {filename}")

    # Save updated content if changed
    if new_content != post.content_md:
        post.content_md = new_content
        post.save()

    return downloaded


def main():
    if len(sys.argv) < 2:
        print("Usage: python download_images.py <wordpress-domain>")
        print("Example: python download_images.py chrisblanduk.com")
        sys.exit(1)

    domain = sys.argv[1]
    base_url = f"https://{domain}"

    print(f"Downloading images from {domain}")
    print(f"Base URL: {base_url}")

    total_downloaded = 0
    posts = Post.objects.all()

    for post in posts:
        print(f"\nProcessing: {post.title}")
        downloaded = process_post_images(post, domain, base_url)
        total_downloaded += downloaded

    print(f"\n\nComplete! Downloaded {total_downloaded} images.")


if __name__ == '__main__':
    main()
