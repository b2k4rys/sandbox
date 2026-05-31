from pydantic import BaseModel, Field, EmailStr
from backend.database import Base
from sqlalchemy import Column, Integer, String


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, index=True, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(Integer)


