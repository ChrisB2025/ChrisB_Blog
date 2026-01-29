#!/bin/bash
set -e

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

# Fix any local image URLs to use WordPress URLs
import re
from django.db import connection

print('Checking for local image URLs to fix...')
fixed_count = 0

for post in Post.objects.all():
    original_md = post.content_md or ''

    # Check if this post has local uploads URLs and show first match
    if '/uploads/' in original_md:
        match = re.search(r'/uploads/[^\s"\'<>)]+', original_md)
        if match:
            print(f'Found in {post.title}: {match.group(0)[:60]}...')

        # Replace local /uploads/ URLs with WordPress URLs
        new_md = re.sub(
            r'/uploads/(?:images/)?(\d{4}/\d{2}/[^)\s"\'<>]+)',
            r'https://chrisblanduk.wordpress.com/wp-content/uploads/\1',
            original_md
        )
        if new_md != original_md:
            # Use direct SQL update to bypass any ORM issues
            Post.objects.filter(pk=post.pk).update(content_md=new_md)
            # Also update content_html by re-fetching and saving
            post.refresh_from_db()
            post.save()  # Regenerates content_html
            fixed_count += 1
            print(f'Fixed: {post.title}')

if fixed_count:
    print(f'Fixed {fixed_count} posts.')
    # Force close connection and re-verify
    connection.close()
    test = Post.objects.filter(title__icontains='Five Generations').first()
    if test:
        print(f'Verify: /uploads/ in content = {"/uploads/" in (test.content_md or "")}')
else:
    print('No posts needed fixing.')
PYTHON_SCRIPT

echo "Starting gunicorn on port $PORT..."
exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --log-level info --access-logfile - --error-logfile - chrisb_blog.wsgi:application
