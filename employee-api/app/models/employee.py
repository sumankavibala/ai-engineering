from typing import TYPE_CHECKING
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from sqlalchemy import String, ForeignKey

if TYPE_CHECKING:
  from app.models.user import User

class Base(DeclarativeBase):
  pass

class Employee(Base):
  __tablename__="employees"

  id: Mapped[int] = mapped_column(
    primary_key=True
  )

  name: Mapped[str] = mapped_column(
    String(100),
    nullable=False
  )

  role: Mapped[str] = mapped_column(
    String(100),
    nullable=False
  )

  experience: Mapped[int] = mapped_column(
    nullable=False
  )

  created_by: Mapped[int] = mapped_column(
    ForeignKey("users.id"),
    nullable=False
  )

  creator: Mapped["User"] = relationship(
    "User",
    back_populates="employees"
  )