from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.employee import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
