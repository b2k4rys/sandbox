from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import create_engine

import settings
from sqlalchemy.orm import sessionmaker, declarative_base


Base = declarative_base()
engine = create_async_engine(settings.DATABASE_URL)
sync_engine = create_engine(settings.SYNC_DATABASE_URL)
AsyncSessionLocal = sessionmaker(bind=engine, class_= AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session