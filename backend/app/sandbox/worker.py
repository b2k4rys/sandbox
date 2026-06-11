from celery import Celery
import os
celery = Celery(__name__, include=["app.sandbox.service"])

celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379")