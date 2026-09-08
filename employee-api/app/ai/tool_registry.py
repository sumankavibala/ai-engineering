from app.ai.tools import INVENTORY_TOOL, POLICY_SEARCH_TOOL

TOOLS = [
  INVENTORY_TOOL,
  POLICY_SEARCH_TOOL,
  ORDER_STATUS_TOOL
]


TOOL_NAME = {
  "get_inventory",
  "search_warehouse_policy",
  "get_order_status"
}