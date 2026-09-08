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
                    "description": "The exact inventory SKU.",
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
        "description": "Search warehouse policies and procedures to answer questions about warehouse rules.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The policy or procedure question.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}
