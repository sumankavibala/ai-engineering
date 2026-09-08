from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user import create_user as create_user_service

router = APIRouter(
  prefix='/users',
  tags=['Users']
)

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, session: AsyncSession = Depends(get_db)):
  try:
    return await create_user_service(session, user)
  except ValueError as error:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
