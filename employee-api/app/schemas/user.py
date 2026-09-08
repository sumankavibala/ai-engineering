from pydantic import BaseModel, Field

class UserCreate(BaseModel):
  username: str = Field(
    min_length=3,
    max_length=100
  )

  password: str = Field(
    min_length=8,
    max_length=128
  )


class UserResponse(BaseModel):
  id: int
  username: str

  model_config = {
    "from_attributes": True
  }

userResponse = UserResponse