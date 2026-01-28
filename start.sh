#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating superuser if not exists..."
python << 'PYTHON_SCRIPT'
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chrisb_blog.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='ChrisB').exists():
    User.objects.create_superuser('ChrisB', 'ChrisB_2023@pm.me', '1eW@$gBPU6J^')
    print('Superuser created.')
else:
    print('Superuser already exists.')
PYTHON_SCRIPT

echo "Starting gunicorn on port $PORT..."
exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --log-level info --access-logfile - --error-logfile - chrisb_blog.wsgi:application
