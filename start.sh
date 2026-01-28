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
PYTHON_SCRIPT

echo "Checking for featured image extraction..."
python << 'PYTHON_SCRIPT'
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chrisb_blog.settings')
django.setup()

from blog.models import Post

# Only run if there are posts without featured images
posts_without_featured = Post.objects.filter(featured_image__isnull=True).count()
if posts_without_featured > 0:
    print(f'Found {posts_without_featured} posts without featured images. Extracting...')
    import sys
    sys.path.insert(0, '/app')
    from scripts.extract_featured_images import main as extract_main
    extract_main()
else:
    print('All posts have featured images. Skipping extraction.')
PYTHON_SCRIPT

echo "Starting gunicorn on port $PORT..."
exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --log-level info --access-logfile - --error-logfile - chrisb_blog.wsgi:application
