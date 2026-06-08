from typing import Annotated

from fastapi import APIRouter, Depends
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User
from sqlalchemy.future import select
from .service import hash_password, verify_password, create_access_token
router = APIRouter(prefix='', tags=['auth_module'])
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
@router.get('/all/users')
async def get_all_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users

@router.post('/register')
async def register(username: str, email: str, password: str ,db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter_by(email=email))
    user = result.scalars().first()
    if user:
        return {"error": "Email is taken"}

    hashed_password = hash_password(password)
    user = User(username=username, email=email, password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post('/token')
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: AsyncSession = Depends(get_db)):
    query = await db.execute(select(User).filter(User.username==form_data.username))
    user = query.scalars().first()
    if verify_password(form_data.password, user.password):
        token = create_access_token({"sub": str(user.id)})
        return {"access_token": token, "token_type": "bearer"}
    return False

