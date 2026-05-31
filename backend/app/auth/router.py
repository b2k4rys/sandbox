from fastapi import APIRouter, Depends
from backend.database import get_db
from sqlalchemy.orm import Session
from .models import User

router = APIRouter(prefix='/auth')

@router.post('/register')
async def register(db: Session = Depends(get_db())):
