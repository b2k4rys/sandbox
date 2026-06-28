from dotenv import load_dotenv
import os
from pathlib import Path


load_dotenv()

DATABASE_URL=os.getenv('DATABASE_URL')
SYNC_DATABASE_URL=os.getenv('SYNC_DATABASE_URL')
token_expire_minutes=os.getenv('TOKEN_EXPIRE_MINUTES')
SECRET_KEY=os.getenv('JWT_SECRET_KEY')
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379")
PAR_DIR = Path(__file__).resolve().parent.parent
SANDBOX_DIR = f'{PAR_DIR}/tmp/sandbox'

RATE_LIMIT = os.getenv("RATE_LIMIT", 3)