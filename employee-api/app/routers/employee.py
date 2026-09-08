from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.employee import (
  EmployeeCreate,
  EmployeeResponse,
  EmployeeUpdate,
  EmployeePatch
)

from app.dependencies import get_db, get_current_user
from app.services.employee import (
    get_employee as get_employee_service,
    get_employee_by_id as get_employee_by_id_service,
    create_employee as create_employee_service,
    update_employee as update_employee_service,
    delete_employee as delete_employee_service,
    patch_employee as patch_employee_service
)

router = APIRouter(
  prefix='/employees',
  tags=['Employees']
)

@router.get("/", response_model=list[EmployeeResponse])
async def get_employee(
  session: AsyncSession = Depends(get_db), 
  current_user = Depends(get_current_user), 
  page: int = Query(1, ge=1),
  page_size: int = Query(20, ge=1, le=100),
  role: str | None = None,
  sort_by: str = "id",
  order: str = "asc",
):
  return await get_employee_service(session, page, page_size, role, sort_by, order)

@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee_by_id(employee_id: int, session: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
  return await get_employee_by_id_service(session, employee_id)

@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(employee: EmployeeCreate, session: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
  return await create_employee_service(session, employee, current_user.id)

@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(employee_id: int, employee_data: EmployeeUpdate, session: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
  return await update_employee_service(session, employee_id, employee_data)

@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(employee_id: int, session: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
  await delete_employee_service(session, employee_id)
  return None

@router.patch('/{employee_id}', response_model=EmployeeResponse)
async def patch_employee(employee_id: int, employee: EmployeePatch, session: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
  try:
    return await patch_employee_service(session, employee_id, employee)
  except ValueError as error:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))