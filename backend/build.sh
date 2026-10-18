#!/usr/bin/env bash
# Render build script: install, collect static files, migrate, seed demo data, create admin.
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py seed_demo
if [[ -n "$DJANGO_SUPERUSER_USERNAME" && -n "$DJANGO_SUPERUSER_PASSWORD" ]]; then
  python manage.py createsuperuser --noinput || true
fi
