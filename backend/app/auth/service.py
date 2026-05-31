from dns.dnssecalgs import algorithms
from jose import jwt
from datetime import datetime, timedelta, UTC
from passlib.context import CryptContext
from backend import settings
pwd_context = CryptContext()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload['exp'] = datetime.now(UTC) + timedelta(minutes=settings.token_expire_minutes)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')