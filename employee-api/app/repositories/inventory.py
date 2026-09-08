from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryItem


class InventoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_sku(self, sku: str) -> InventoryItem | None:
        statement = select(InventoryItem).where(InventoryItem.sku == sku)
        return await self.db.scalar(statement)
