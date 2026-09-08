from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.employee import Base

class InventoryItem(Base):
  __tablename__ = "inventory_items"

  id: Mapped[int] = mapped_column(
    primary_key=True
  )

  sku: Mapped[str] = mapped_column(
    String(100),
    unique=True,
    nullable=False
  )

  product_name: Mapped[str] = mapped_column(
    String(255),
    nullable=False
  )

  quantity: Mapped[int] = mapped_column(
    Integer,
    nullable=False
  )

  warehouse_location: Mapped[str] = mapped_column(
    String(100),
    nullable=False
  )