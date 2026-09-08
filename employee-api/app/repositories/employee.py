from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models.employee import Employee
from app.schemas.employee import EmployeeUpdate


async def get_all(session: AsyncSession, offset: int, limit: int, role: Optional[str], sort_by: str, order: str):
    SORTABLE_FIELDS = { 
        "id": Employee.id, 
        "name": Employee.name, 
        "experience": Employee.experience 
    }
    
    # 1. Validate the sort field
    sort_column = SORTABLE_FIELDS.get(sort_by)
    if sort_column is None:
        raise ValueError(f"Invalid sort field: {sort_by}. Sortable fields are: {', '.join(SORTABLE_FIELDS.keys())}")
    
    # 2. Initialize the base query statement
    statement = select(Employee)
    
    # 3. Apply filters
    if role:
        statement = statement.where(Employee.role == role)
        
    # 4. Apply ordering
    if order == "desc":
        statement = statement.order_by(sort_column.desc())
    else:
        statement = statement.order_by(sort_column.asc())
        
    # 5. Apply pagination
    statement = statement.offset(offset).limit(limit)
    
    # 6. Execute and return results
    result = await session.execute(statement)
    return result.scalars().all()

async def get_by_id(session: AsyncSession, employee_id: int):
    statement = select(Employee).where(Employee.id == employee_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()

async def create(session: AsyncSession, employee: Employee):
    session.add(employee)
    await session.flush()
    return employee

async def update(session: AsyncSession, employee: Employee, employee_data: EmployeeUpdate):
    employee.name = employee_data.name
    employee.role = employee_data.role
    employee.experience = employee_data.experience
    await session.flush()
    return employee

async def delete(session: AsyncSession, employee: Employee):
    await session.delete(employee)
    await session.flush()

async def update_fields(session: AsyncSession, employee: Employee, fields: dict):
    for field, value in fields.items():
        setattr(employee, field, value)
    await session.flush()
    return employee