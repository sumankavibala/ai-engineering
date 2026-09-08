from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionLocal
from app.repositories import user as user_repository

oauth2_scheme = OAuth2PasswordBearer(
  tokenUrl="auth/login"
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
  async with SessionLocal() as session:
    yield session

async def get_current_user(
  token: str = Depends(oauth2_scheme),
  db: AsyncSession = Depends(get_db)
):
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
  )
  
  try:
    payload = jwt.decode(
      token,
      settings.jwt_secret_key,
      algorithms=[settings.jwt_algorithm],
    )

    user_id = payload.get("sub")
    if not user_id:
      raise credentials_exception
      
    user_id = int(user_id)
  except (InvalidTokenError, ValueError):
    raise credentials_exception

  user = await user_repository.get_by_id(db, user_id)
  if not user:
    raise credentials_exception
    
  return user
    