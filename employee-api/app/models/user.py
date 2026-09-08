from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.employee import Base

if TYPE_CHECKING:
  from app.models.employee import Employee

class User(Base):
  __tablename__ = "users"

  id: Mapped[int] = mapped_column(
    primary_key = True
  )

  username: Mapped[str] = mapped_column(
    String(100),
    unique=True,
    nullable=False
  )

  password_hash: Mapped[str] = mapped_column(
    String(255),
    nullable = False
  )

  employees: Mapped[list["Employee"]] = relationship(
    "Employee",
    back_populates="creator"
  )