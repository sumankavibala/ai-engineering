INVENTORY_TOOL = {
    "type": "function",
    "function": {
        "name": "get_inventory",
        "description": "Get the current inventory quantity and warehouse location for a SKU.",
        "parameters": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Exact inventory SKU.",
                }
            },
            "required": ["sku"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}

POLICY_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_warehouse_policy",
        "description": "Search warehouse policies and procedures for information warehouse rules.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The warehouse policy question to search for.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}

ORDER_STATUS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_order_status",
        "description": "Get the current status and details of a warehouse order.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "Warehouse order ID."
                }
            },
            "required": ["order_id"],
            "additionalProperties": False
        },
        "strict": True
    },
}