from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.inventory import InventoryRepository

class InventoryService:
  def __init__(self, db: AsyncSession):
    self.repository = InventoryRepository(db)

  async def get_inventory(self, sku: str):
    item = await self.repository.get_by_sku(sku)
    
    if not item:
      return {
        "found": False,
        "sku": sku
      }

    return {
      "found": True,
      "sku": item.sku,
      "product_name": item.product_name,
      "quantity": item.quantity,
      "warehouse_location": item.warehouse_location
    }