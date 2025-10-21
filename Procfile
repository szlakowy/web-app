web: gunicorn demo.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A demo.celery worker -l info
