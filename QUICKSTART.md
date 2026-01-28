# ChrisB Blog - Quick Start Guide

Self-hosted Django blog migrated from WordPress with HTMX frontend and AI image generation.

## Setup

```bash
# Install Poetry if not installed
pip install poetry

# Install dependencies
cd C:\Dev\Claude\ChrisB_Blog
poetry install

# Create .env file from example
cp .env.example .env
# Edit .env with your settings

# Run migrations
poetry run python manage.py migrate

# Create superuser
poetry run python manage.py createsuperuser

# Run development server
poetry run python manage.py runserver
```

## Common Commands

```bash
# Development server
poetry run python manage.py runserver

# Create migrations after model changes
poetry run python manage.py makemigrations

# Apply migrations
poetry run python manage.py migrate

# Create superuser
poetry run python manage.py createsuperuser

# Collect static files
poetry run python manage.py collectstatic

# Run Celery worker (for AI image generation)
poetry run celery -A chrisb_blog worker -l info

# Import WordPress content
poetry run python scripts/migrate_wordpress.py path/to/export.xml

# Download WordPress images
poetry run python scripts/download_images.py chrisblanduk.com
```

## Key URLs

| URL | Description |
|-----|-------------|
| `/` | Home page |
| `/admin/` | Django admin |
| `/editor/` | Custom post editor |
| `/imagen/` | AI image generator |
| `/feed/` | RSS feed |
| `/sitemap.xml` | Sitemap |
| `/health/` | Health check endpoint |

## Key Files

| File | Purpose |
|------|---------|
| `chrisb_blog/settings.py` | Django configuration |
| `blog/models.py` | Post, Tag, Comment, Image models |
| `blog/views.py` | Public blog views |
| `editor/views.py` | HTMX editor views |
| `imagen/services.py` | Vertex AI integration |
| `templates/base.html` | Base template |
| `static/css/style.css` | WordPress theme match |

## Project Structure

```
ChrisB_Blog/
├── chrisb_blog/          # Django project config
├── blog/                 # Core blog app
├── editor/               # Post editor app
├── imagen/               # AI image generation app
├── analytics/            # Page view tracking
├── templates/            # Django templates
│   ├── base.html
│   ├── blog/
│   ├── editor/
│   └── components/
├── static/               # CSS, JS
├── scripts/              # Migration scripts
├── Dockerfile
└── railway.toml
```

## Environment Variables

```env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgresql://...     # Leave empty for SQLite
REDIS_URL=redis://...             # Leave empty for memory cache
GOOGLE_CLOUD_PROJECT=...          # For AI images
VERTEX_AI_LOCATION=us-central1
```

## Railway Deployment

1. Create Railway project
2. Add PostgreSQL and Redis services
3. Add persistent volume for `/app/uploads`
4. Set environment variables
5. Deploy from GitHub

## For AI Assistants (Claude)

1. **First**: Read `STRUCTURE.json` for architecture overview
2. **Then**: Check `PROJECT_NOTES.md` for current context and decisions
3. **Check**: `tasks.json` for pending tasks
4. **Follow**: Existing code patterns and conventions
5. **Update**: These files as you make changes

## Current State

- Django project fully set up with all apps
- Models created: Post, Tag, Comment, Image, Profile, PageView
- Public views: home, post detail, tag pages, search, about
- Editor: HTMX-powered markdown editor with EasyMDE
- AI images: Vertex AI Imagen 4 integration with Celery tasks
- Templates: WordPress theme colors (burgundy/red) matched
- Ready for WordPress migration and Railway deployment
