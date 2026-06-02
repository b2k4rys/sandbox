from fastapi import APIRouter, Depends
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User
from sqlalchemy.future import select
from .service import hash_password, verify_password, create_access_token
router = APIRouter(prefix='/auth', tags=['auth_module'])

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

@router.post('/login')
async def login(email: str, password: str, db: AsyncSession = Depends(get_db)):
    query = await db.execute(select(User).filter(User.email==email))
    user = query.scalars().first()
    if verify_password(password, user.password):
        token = create_access_token({"sub": str(user.id)})
        return token
    return False

