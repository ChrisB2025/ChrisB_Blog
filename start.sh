#!/bin/bash
set -e

# Ensure uploads directory exists with correct permissions
echo "Setting up uploads directory..."
UPLOAD_DIR="${UPLOADS_PATH:-/app/uploads}"
mkdir -p "$UPLOAD_DIR/images" 2>/dev/null || true
chmod -R 755 "$UPLOAD_DIR" 2>/dev/null || true

echo "Running migrations..."
python manage.py migrate --noinput

echo "Checking for WordPress import..."
python << 'PYTHON_SCRIPT'
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chrisb_blog.settings')
django.setup()

from blog.models import Post

# Only run import if no posts exist yet
if Post.objects.count() == 0:
    print('No posts found. Running WordPress import...')
    import sys
    sys.path.insert(0, '/app')
    from scripts.migrate_wordpress import parse_wordpress_xml, import_data
    from django.contrib.auth import get_user_model
    User = get_user_model()

    xml_path = '/app/.Assets/chrisb039sblog.WordPress.2026-01-28.xml'
    if os.path.exists(xml_path):
        data = parse_wordpress_xml(xml_path)
        print(f'Found {len(data["tags"])} tags, {len(data["posts"])} posts')

        # Use ChrisB as default author
        default_author = User.objects.filter(username='ChrisB').first() or User.objects.first()
        stats = import_data(data, default_author)

        print(f'Import complete: {stats["posts_created"]} posts, {stats["tags_created"]} tags, {stats["comments_created"]} comments')
    else:
        print(f'WordPress XML not found at {xml_path}')
else:
    print(f'Posts already exist ({Post.objects.count()}). Skipping WordPress import.')

# Fix corrupted URLs in database (one-time repair)
# Previous startup script corrupted URLs by repeatedly adding WordPress prefix
import re

def fix_corrupted_url(text):
    """Fix URLs with repeated WordPress prefixes."""
    if not text:
        return text

    # Pattern 1: repeated chrisblanduk.wordpress.com prefixes
    pattern1 = r'(https://chrisblanduk\.wordpress\.com/wp-content)(?:https://chrisblanduk\.wordpress\.com/wp-content)+(/uploads/\d{4}/\d{2}/[^)\s"\'<>\]]+)'
    text = re.sub(pattern1, r'\1\2', text)

    # Pattern 2: chrisblanduk.com followed by chrisblanduk.wordpress.com
    pattern2 = r'https://chrisblanduk\.com/wp-content(?:https://chrisblanduk\.wordpress\.com/wp-content)+(/uploads/\d{4}/\d{2}/[^)\s"\'<>\]]+)'
    text = re.sub(pattern2, r'https://chrisblanduk.wordpress.com/wp-content\1', text)

    # Pattern 3: any remaining wp-contenthttps sequences
    pattern3 = r'(https://[^/]+/wp-content)https://[^/]+/wp-content(/uploads/[^)\s"\'<>\]]+)'
    text = re.sub(pattern3, r'\1\2', text)

    return text

print('Checking for corrupted URLs to repair...')
repaired = 0
for post in Post.objects.all():
    original_md = post.content_md or ''
    fixed_md = fix_corrupted_url(original_md)

    if fixed_md != original_md:
        post.content_md = fixed_md
        post.save()  # This also regenerates content_html
        repaired += 1
        print(f'Repaired: {post.title}')

if repaired:
    print(f'Repaired {repaired} posts with corrupted URLs.')
else:
    print('No corrupted URLs found.')
PYTHON_SCRIPT

# Check if running as worker
if [ "$WORKER_MODE" = "true" ]; then
    echo "Starting Celery worker..."
    exec celery -A chrisb_blog worker --loglevel=info
else
    echo "Starting gunicorn on port $PORT..."
    exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --log-level info --access-logfile - --error-logfile - chrisb_blog.wsgi:application
fi
