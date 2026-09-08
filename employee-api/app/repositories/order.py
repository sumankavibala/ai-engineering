from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.order import Order


class OrderRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_order_status(self, order_id: int) -> Order | None:
        statement = select(Order).where(Order.id == order_id)
        return await self.db.scalar(statement)

