import os
from celery import Celery

# Ustaw domyślną zmienną środowiskową DJANGO_SETTINGS_MODULE dla 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo.settings')

app = Celery('demo')

# Użyj stringa tutaj, aby worker nie musiał serializować
# obiektu konfiguracyjnego do procesów potomnych.
# - namespace='CELERY' oznacza, że wszystkie ustawienia Celery
#   muszą mieć prefiks `CELERY_` w settings.py.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatycznie odkrywaj zadania z wszystkich zarejestrowanych aplikacji Django.
app.autodiscover_tasks()
