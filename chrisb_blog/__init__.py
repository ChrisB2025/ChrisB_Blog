"""
ChrisB Blog - Self-hosted Django blog with HTMX.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
