from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import user as user_repository
from app.schemas.user import UserCreate
from app.security import hash_password

async def create_user(session: AsyncSession, user_data: UserCreate): 

  existing_user = await user_repository.get_by_username(
    session, user_data.username
  )

  if existing_user is not None:
    raise ValueError(
      "Username already exists"
    )

  password_hash = hash_password(
    user_data.password
  )

  user = User(username=user_data.username, password_hash=password_hash)

  await user_repository.create(
    session, user
  )
  await session.commit()
  await session.refresh(user)

  return user