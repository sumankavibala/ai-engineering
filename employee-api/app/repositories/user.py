from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

async def get_by_username(session: AsyncSession, username: str):
  statement = select(User).where(User.username == username)
  result = await session.execute(statement)
  return result.scalar_one_or_none()

async def create(session: AsyncSession, user: User):
  session.add(user)
  await session.flush()
  return user

async def get_by_id(session: AsyncSession, user_id: int):
  statement = select(User).where(User.id == user_id)
  result = await session.execute(statement)
  return result.scalar_one_or_none()