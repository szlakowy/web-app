web: sh -c "gunicorn demo.wsgi:application --bind 0.0.0.0:${PORT:-8000}"
worker: celery -A demo.celery worker -l info
