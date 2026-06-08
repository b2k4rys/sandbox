from jose import jwt
from datetime import datetime, timedelta, UTC
from pwdlib import PasswordHash
import settings
from .models import User
from fastapi import Depends, HTTPException, status
from typing import Annotated
from database import get_db
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(password=plain, hash=hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload['exp'] = datetime.now(UTC) + timedelta(minutes=int(settings.token_expire_minutes))
    return jwt.encode(payload, str(settings.SECRET_KEY), algorithm='HS256')

def decode_jwt(token: str):
    return jwt.decode(token, key=str(settings.SECRET_KEY), algorithms=['HS256'])


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: AsyncSession = Depends(get_db)):
    decoded_jwt = decode_jwt(token)
    user_id = int(decoded_jwt['sub'])
    if user_id:
        result = await db.execute(select(User).filter_by(id=user_id))
        user = result.scalars().first()
        return user
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)