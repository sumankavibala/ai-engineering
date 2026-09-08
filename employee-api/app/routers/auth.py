from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import login as login_service

router = APIRouter(
  prefix="/auth",
  tags=["Authentication"]
)

@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, session: AsyncSession = Depends(get_db)):
  token = await login_service(
    session,
    credentials.username,
    credentials.password
  )

  if token is None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
  
  return TokenResponse(
    access_token=token,
    token_type="bearer"
  )
  