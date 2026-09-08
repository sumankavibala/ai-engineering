from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeePatch

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.employee import Employee
from app.repositories import employee as employee_repository
from app.exceptions import EmployeeNotFoundError

async def get_employee(session: AsyncSession, page: int, page_size: int, role: str | None, sort_by: str, order: str):
  offset = (page - 1) * page_size
  return await employee_repository.get_all(session, offset, page_size, role, sort_by, order)


async def get_employee_by_id(session: AsyncSession, id: int):
  employee = await employee_repository.get_by_id(session, id)
  if employee is None:
    raise EmployeeNotFoundError(f"Employee with ID {id} not found")
  return employee  


async def create_employee(session: AsyncSession, employee_data: EmployeeCreate, current_user_id: int):
  employee = Employee(
    name=employee_data.name,
    role=employee_data.role,
    experience=employee_data.experience,
    created_by=current_user_id
  )

  await employee_repository.create(session, employee)
  await session.commit()
  await session.refresh(employee)

  return employee


async def update_employee(
  session: AsyncSession,
  employee_id: int,
  employee_data: EmployeeUpdate
): 
  employee = await employee_repository.get_by_id(session, employee_id)
  if employee is None:
    raise EmployeeNotFoundError(f"Employee with ID {employee_id} not found")
  
  await employee_repository.update(session, employee, employee_data)
  await session.commit()
  await session.refresh(employee)

  return employee


async def delete_employee(
  session: AsyncSession,
  employee_id: int
):
  employee = await employee_repository.get_by_id(session, employee_id)

  if employee is None:
    raise EmployeeNotFoundError(f"Employee with ID {employee_id} not found")

  await employee_repository.delete(session, employee)
  await session.commit()

  return True


async def patch_employee(session: AsyncSession, employee_id: int, employee_data: EmployeePatch):
  employee = await employee_repository.get_by_id(session, employee_id)

  if employee is None:
    raise EmployeeNotFoundError(f"Employee with ID {employee_id} not found")

  fields = employee_data.model_dump(exclude_unset=True)

  if not fields:
    raise ValueError("At least one field is required")

  await employee_repository.update_fields(session, employee, fields)
  await session.commit()
  await session.refresh(employee)

  return employee