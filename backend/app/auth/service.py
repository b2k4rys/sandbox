from dns.dnssecalgs import algorithms
from jose import jwt
from datetime import datetime, timedelta, UTC
from pwdlib import PasswordHash
import settings

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(password=plain, hash=hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload['exp'] = datetime.now(UTC) + timedelta(minutes=int(settings.token_expire_minutes))
    return jwt.encode(payload, str(settings.SECRET_KEY), algorithm='HS256')