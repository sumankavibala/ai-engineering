from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.order import OrderRepository

from langchain.tools import tool

class OrderService:

    def __init__(self, db: AsyncSession):
        self.repository = OrderRepository(db)

    async def get_order_status(self, order_id: int):
        """Get the current status and details of a warehouse order."""
        order = await self.repository.get_order_status(order_id)

        if not order:
            return {"found": False, "order_id": order_id}

        return {
            "found": True,
            "order_id": order.id,
            "status": order.status,
            "sku": order.sku,
            "quantity": order.quantity,
        }
