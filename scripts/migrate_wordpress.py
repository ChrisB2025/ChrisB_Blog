#!/usr/bin/env python
"""
WordPress XML Export Migration Script

This script imports posts, tags, comments, and images from a WordPress XML export.

Usage:
    python scripts/migrate_wordpress.py path/to/wordpress-export.xml

Requirements:
    - Django settings must be configured
    - Database must be migrated
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chrisb_blog.settings')

import django
django.setup()

from django.contrib.auth.models import User
from django.utils.text import slugify

from blog.models import Comment, CommentStatus, Image, Post, PostStatus, Tag


# WordPress XML namespaces
WP_NS = {'wp': 'http://wordpress.org/export/1.2/'}
CONTENT_NS = {'content': 'http://purl.org/rss/1.0/modules/content/'}
DC_NS = {'dc': 'http://purl.org/dc/elements/1.1/'}


def parse_wordpress_xml(xml_path: str) -> dict:
    """Parse WordPress XML export file."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    channel = root.find('channel')

    return {
        'tags': parse_tags(channel),
        'posts': parse_posts(channel),
        'authors': parse_authors(channel),
    }


def parse_tags(channel) -> list[dict]:
    """Extract tags from WordPress export (ignoring categories)."""
    tags = []
    for tag in channel.findall('wp:tag', WP_NS):
        tags.append({
            'term_id': int(tag.find('wp:term_id', WP_NS).text),
            'slug': tag.find('wp:tag_slug', WP_NS).text,
            'name': tag.find('wp:tag_name', WP_NS).text,
        })
    return tags


def parse_authors(channel) -> list[dict]:
    """Extract authors from WordPress export."""
    authors = []
    for author in channel.findall('wp:author', WP_NS):
        authors.append({
            'login': author.find('wp:author_login', WP_NS).text,
            'email': author.find('wp:author_email', WP_NS).text or '',
            'display_name': author.find('wp:author_display_name', WP_NS).text or '',
        })
    return authors


def parse_posts(channel) -> list[dict]:
    """Extract posts from WordPress export."""
    posts = []
    for item in channel.findall('item'):
        post_type = item.find('wp:post_type', WP_NS)
        if post_type is None or post_type.text != 'post':
            continue

        # Get post status
        wp_status = item.find('wp:status', WP_NS).text
        if wp_status == 'publish':
            status = 'published'
        elif wp_status == 'draft':
            status = 'draft'
        elif wp_status == 'future':
            status = 'scheduled'
        else:
            continue  # Skip trash, private, etc.

        # Parse date
        pub_date = item.find('pubDate').text
        if pub_date:
            try:
                published_at = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')
            except ValueError:
                published_at = None
        else:
            published_at = None

        # Get content
        content_encoded = item.find('content:encoded', CONTENT_NS)
        content = content_encoded.text if content_encoded is not None and content_encoded.text else ''

        # Get excerpt
        excerpt_encoded = item.find('excerpt:encoded', {'excerpt': 'http://wordpress.org/export/1.2/excerpt/'})
        excerpt = excerpt_encoded.text if excerpt_encoded is not None and excerpt_encoded.text else ''

        # Get tags (skip categories)
        tags = []
        for category in item.findall('category'):
            if category.get('domain') == 'post_tag':
                tags.append(category.get('nicename'))

        # Get comments
        comments = []
        for comment in item.findall('wp:comment', WP_NS):
            comment_approved = comment.find('wp:comment_approved', WP_NS).text
            if comment_approved == '1':
                comment_status = 'approved'
            elif comment_approved == 'spam':
                comment_status = 'spam'
            else:
                comment_status = 'pending'

            comment_date = comment.find('wp:comment_date', WP_NS).text
            try:
                comment_created = datetime.strptime(comment_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                comment_created = None

            comments.append({
                'id': int(comment.find('wp:comment_id', WP_NS).text),
                'parent': int(comment.find('wp:comment_parent', WP_NS).text or 0),
                'author_name': comment.find('wp:comment_author', WP_NS).text or 'Anonymous',
                'author_email': comment.find('wp:comment_author_email', WP_NS).text or '',
                'content': comment.find('wp:comment_content', WP_NS).text or '',
                'status': comment_status,
                'created_at': comment_created,
            })

        posts.append({
            'id': int(item.find('wp:post_id', WP_NS).text),
            'title': item.find('title').text or 'Untitled',
            'slug': item.find('wp:post_name', WP_NS).text,
            'content': content,
            'excerpt': excerpt,
            'status': status,
            'author': item.find('dc:creator', DC_NS).text,
            'published_at': published_at,
            'tags': tags,
            'comments': comments,
        })

    return posts


def html_to_markdown(html: str) -> str:
    """Convert WordPress HTML content to Markdown."""
    if not html:
        return ''

    # Basic conversions
    md = html

    # Headings
    md = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', md, flags=re.DOTALL)
    md = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', md, flags=re.DOTALL)
    md = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', md, flags=re.DOTALL)
    md = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n', md, flags=re.DOTALL)

    # Bold and italic
    md = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', md, flags=re.DOTALL)
    md = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', md, flags=re.DOTALL)
    md = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', md, flags=re.DOTALL)
    md = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', md, flags=re.DOTALL)

    # Links
    md = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', md, flags=re.DOTALL)

    # Images
    md = re.sub(r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>',
                r'![\2](\1)', md, flags=re.DOTALL)
    md = re.sub(r'<img[^>]*src="([^"]*)"[^>]*/?>',
                r'![](\1)', md, flags=re.DOTALL)

    # Lists
    md = re.sub(r'<ul[^>]*>', '', md)
    md = re.sub(r'</ul>', '\n', md)
    md = re.sub(r'<ol[^>]*>', '', md)
    md = re.sub(r'</ol>', '\n', md)
    md = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', md, flags=re.DOTALL)

    # Code blocks
    md = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>',
                r'```\n\1\n```\n', md, flags=re.DOTALL)
    md = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', md, flags=re.DOTALL)

    # Blockquotes
    md = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>',
                lambda m: '> ' + m.group(1).strip().replace('\n', '\n> ') + '\n',
                md, flags=re.DOTALL)

    # Paragraphs and line breaks
    md = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', md, flags=re.DOTALL)
    md = re.sub(r'<br\s*/?>', '\n', md)
    md = re.sub(r'<hr\s*/?>', '\n---\n', md)

    # Remove remaining HTML tags
    md = re.sub(r'<[^>]+>', '', md)

    # Clean up whitespace
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = md.strip()

    return md


def import_data(data: dict, default_author: User) -> dict:
    """Import parsed WordPress data into Django models."""
    stats = {
        'tags_created': 0,
        'posts_created': 0,
        'comments_created': 0,
    }

    # Create author mapping
    authors = {}
    for wp_author in data['authors']:
        user, created = User.objects.get_or_create(
            username=wp_author['login'],
            defaults={
                'email': wp_author['email'],
                'first_name': wp_author['display_name'].split()[0] if wp_author['display_name'] else '',
                'last_name': ' '.join(wp_author['display_name'].split()[1:]) if wp_author['display_name'] else '',
            }
        )
        authors[wp_author['login']] = user

    # Import tags
    tag_map = {}
    for wp_tag in data['tags']:
        tag, created = Tag.objects.get_or_create(
            slug=wp_tag['slug'],
            defaults={
                'name': wp_tag['name'],
                'wp_term_id': wp_tag['term_id'],
            }
        )
        tag_map[wp_tag['slug']] = tag
        if created:
            stats['tags_created'] += 1

    # Import posts
    for wp_post in data['posts']:
        # Get author
        author = authors.get(wp_post['author'], default_author)

        # Convert content to markdown
        content_md = html_to_markdown(wp_post['content'])

        # Determine status
        status_map = {
            'published': PostStatus.PUBLISHED,
            'draft': PostStatus.DRAFT,
            'scheduled': PostStatus.SCHEDULED,
        }
        status = status_map.get(wp_post['status'], PostStatus.DRAFT)

        # Create or update post
        post, created = Post.objects.update_or_create(
            wp_post_id=wp_post['id'],
            defaults={
                'title': wp_post['title'],
                'slug': wp_post['slug'] or slugify(wp_post['title']),
                'content_md': content_md,
                'excerpt': wp_post['excerpt'] or '',
                'status': status,
                'author': author,
                'published_at': wp_post['published_at'],
            }
        )

        # Add tags
        for tag_slug in wp_post['tags']:
            if tag_slug in tag_map:
                post.tags.add(tag_map[tag_slug])

        if created:
            stats['posts_created'] += 1

        # Import comments
        comment_map = {}  # Map WP comment ID to Django comment
        for wp_comment in sorted(wp_post['comments'], key=lambda c: c['id']):
            status_map = {
                'approved': CommentStatus.APPROVED,
                'pending': CommentStatus.PENDING,
                'spam': CommentStatus.SPAM,
            }

            parent = None
            if wp_comment['parent'] and wp_comment['parent'] in comment_map:
                parent = comment_map[wp_comment['parent']]

            comment, created = Comment.objects.update_or_create(
                wp_comment_id=wp_comment['id'],
                defaults={
                    'post': post,
                    'parent': parent,
                    'author_name': wp_comment['author_name'],
                    'author_email': wp_comment['author_email'],
                    'content': wp_comment['content'],
                    'status': status_map.get(wp_comment['status'], CommentStatus.PENDING),
                }
            )

            # Manually set created_at if available
            if wp_comment['created_at'] and created:
                Comment.objects.filter(pk=comment.pk).update(created_at=wp_comment['created_at'])

            comment_map[wp_comment['id']] = comment

            if created:
                stats['comments_created'] += 1

    return stats


def main():
    if len(sys.argv) < 2:
        print("Usage: python migrate_wordpress.py <wordpress-export.xml>")
        sys.exit(1)

    xml_path = sys.argv[1]
    if not os.path.exists(xml_path):
        print(f"Error: File not found: {xml_path}")
        sys.exit(1)

    print(f"Parsing WordPress export: {xml_path}")
    data = parse_wordpress_xml(xml_path)

    print(f"Found {len(data['tags'])} tags")
    print(f"Found {len(data['posts'])} posts")
    print(f"Found {len(data['authors'])} authors")

    # Get or create default author
    default_author, _ = User.objects.get_or_create(
        username='admin',
        defaults={'is_staff': True, 'is_superuser': True}
    )

    print("\nImporting data...")
    stats = import_data(data, default_author)

    print("\nMigration complete!")
    print(f"  Tags created: {stats['tags_created']}")
    print(f"  Posts created: {stats['posts_created']}")
    print(f"  Comments created: {stats['comments_created']}")


if __name__ == '__main__':
    main()
