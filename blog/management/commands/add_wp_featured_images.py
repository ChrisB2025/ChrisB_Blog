"""
Management command to add WordPress featured images to posts that are missing them.

These featured images exist on WordPress but weren't included in the post content
during the original import.
"""
from django.core.management.base import BaseCommand
from blog.models import Post


class Command(BaseCommand):
    help = 'Add WordPress featured images to posts missing them'

    # WordPress featured images that weren't imported into content
    WP_FEATURED_IMAGES = {
        'the-church-of-the-invisible-hand': 'https://chrisblanduk.com/wp-content/uploads/2025/03/image-1.png',
        'congratulations-youre-already-a-millionaire': 'https://chrisblanduk.com/wp-content/uploads/2025/03/image.png',
        'humanitys-achilles-heel': 'https://chrisblanduk.com/wp-content/uploads/2025/01/image.png',
        'sortition-in-dao-governance-a-potential-solution-to-voting-vulnerability': 'https://chrisblanduk.com/wp-content/uploads/2023/06/scs3vegcnt671.webp',
    }

    def handle(self, *args, **options):
        updated = 0
        skipped = 0

        for slug, img_url in self.WP_FEATURED_IMAGES.items():
            try:
                post = Post.objects.get(slug=slug)

                # Check if already has an image
                if post.thumbnail_url:
                    self.stdout.write(f'SKIP {slug} - already has thumbnail')
                    skipped += 1
                    continue

                # Add image at the beginning of content_md
                img_md = f'![]({img_url})\n\n'
                post.content_md = img_md + post.content_md
                post.save()  # This will re-render content_html

                self.stdout.write(self.style.SUCCESS(f'UPDATED {slug}'))
                self.stdout.write(f'  New thumbnail_url: {post.thumbnail_url}')
                updated += 1

            except Post.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'NOT FOUND: {slug}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Done. Updated: {updated}, Skipped: {skipped}'))
