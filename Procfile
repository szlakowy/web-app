web: gunicorn demo.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A demo.celery worker -l info
# Jeśli używasz zadań okresowych:
# beat: celery -A demo.celery beat -l info
