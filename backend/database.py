from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


from backend import settings
from sqlalchemy.orm import sessionmaker, declarative_base


Base = declarative_base()
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session