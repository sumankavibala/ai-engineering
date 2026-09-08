from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker, create_async_engine)

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{settings.database_user}:{settings.database_password}"
    f"@{settings.database_host}:{settings.database_port}"
    f"/{settings.database_name}"
)

engine = create_async_engine(DATABASE_URL)

SessionLocal = async_sessionmaker(
  engine,
  expire_on_commit=False
)