from app.services.inventory import InventoryService
from app.services.order import OrderService
from app.services.rag import RAGService


class ToolService:
    def __init__(self, inventory_service: InventoryService, order_service: OrderService, rag_service: RAGService):
        self.inventory_service = inventory_service
        self.order_service = order_service
        self.rag_service = rag_service

    def execute(self, tool_name: str, arguments: dict):
        if tool_name == "get_inventory":
            return self.inventory_service.get_inventory(sku=arguments["sku"])

        if tool_name == "search_warehouse_policy":
            return self.inventory_service.search(question=arguments["query"])

        if tool_name == "get_order_status":
            return self.order_service.get_order_status(order_id=arguments["order_id"])

        raise ValueError(f"Unkown tool: {tool_name}")
