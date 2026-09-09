import json
import re

from app.ai.client import client
from app.ai.tools import INVENTORY_TOOL, POLICY_SEARCH_TOOL, ORDER_STATUS_TOOL


def strip_thinking_tags(text: str | None) -> str:
    if not text:
        return ""
    # Strip complete <think>...</think> blocks as well as unclosed <think>... blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL)
    return text.strip()

class AIAgentService:
    def __init__(self, inventory_service, rag_service, order_service=None):
        self.inventory_service = inventory_service
        self.rag_service = rag_service
        self.order_service = order_service

    async def ask(self, question: str):
        messages = [{"role": "user", "content": question}]

        start = time.perf_counter()

        response = client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=messages,
            tools=[INVENTORY_TOOL, POLICY_SEARCH_TOOL, ORDER_STATUS_TOOL],
            max_tokens=500,
        )

        print(
            "llm_call",
            extra={
                "latency_seconds": elapsed
            }
        )

        message = response.choices[0].message

        if not message.tool_calls:
            return strip_thinking_tags(message.content)

        messages.append(message)

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            if name == "get_inventory":
                sku = arguments.get("sku")
                result = await self.inventory_service.get_inventory(sku=sku)
            elif name == "search_warehouse_policy":
                query = arguments.get("query")
                result = await self.rag_service.ask(question=query)
            elif name == "get_order_status":
                order_id = arguments.get("order_id")
                # Call order service (or await if async)
                if self.order_service:
                    result = await self.order_service.get_order_status(order_id=order_id)
                else:
                    result = {"error": "Order service unavailable"}
            else:
                result = {"error": f"Unknown tool: {name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

        start = time.perf_counter()

        final_response = client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=messages,
            max_tokens=1000,
        )

        print(
            "llm_call",
            extra={
                "latency_seconds": elapsed
            }
        )

        return strip_thinking_tags(final_response.choices[0].message.content)
