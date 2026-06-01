from fastapi import APIRouter, Depends
from database import get_db
from sqlalchemy.orm import Session
from .models import User
from sqlalchemy.future import select
router = APIRouter(prefix='/auth', tags=['auth_module'])

@router.post('/register')
async def register(item = "str", db: Session = Depends(get_db)):
    new_user = User(username="beka")
    db.add(new_user)
    db.commit()
    result = await db.execute(select(User))
    users = result.scalars().all()
    print(users)
    return item
