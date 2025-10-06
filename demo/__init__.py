# To zapewni, że aplikacja Celery zostanie załadowana, gdy Django się uruchomi.
from .celery import app as celery_app

__all__ = ('celery_app',)