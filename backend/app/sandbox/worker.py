from celery import Celery
import settings
celery = Celery(__name__, include=["app.sandbox.service"])


celery.conf.broker_url = settings.CELERY_BROKER_URL
celery.conf.result_backend = settings.CELERY_RESULT_BACKEND