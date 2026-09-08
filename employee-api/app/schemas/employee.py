from pydantic import BaseModel, Field

class EmployeeCreate(BaseModel):
  name: str = Field(min_length=2, max_length=100)
  role: str = Field(min_length=2, max_length=100)
  experience: int = Field(ge=0,le=50)

class EmployeeUpdate(BaseModel):
  name: str = Field(min_length=2, max_length=100)
  role: str = Field(min_length=2, max_length=100)
  experience: int = Field(ge=0, le=50)

class EmployeePatch(BaseModel):
  name: str | None = Field(default=None, min_length=2, max_length=100)
  role: str | None = Field(default=None, min_length=2, max_length=100)
  experience: int | None = Field(default=None, ge=0, le=50)

class EmployeeResponse(BaseModel):
  id: int
  name: str
  role: str
  experience: int

  model_config = {
    "from_attributes": True
  }


