from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import user as user_repository
from app.security import create_access_token, verify_password

async def login(session: AsyncSession, username: str, password: str):
  user = await user_repository.get_by_username(
    session, username
  )

  if user is None:
    return None
  
  if not verify_password(
    password, user.password_hash
  ):
    return None

  return create_access_token(user.id)