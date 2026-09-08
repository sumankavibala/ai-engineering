import json

from app.ai.client import client
from app.ai.tools import INVENTORY_TOOL


class AIAgentService:
    def __init__(self, inventory_service):
        self.inventory_service = inventory_service

    async def ask(self, question: str):
        messages = [{"role": "user", "content": question}]

        response = client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=messages,
            tools=[INVENTORY_TOOL],
            max_tokens=500,
        )

        message = response.choices[0].message

        if not message.tool_calls:
            return message.content

        messages.append(message)

        for tool_call in message.tool_calls:
            if tool_call.function.name == "get_inventory":
                arguments = json.loads(tool_call.function.arguments)
                sku = arguments.get("sku")

                result = await self.inventory_service.get_inventory(sku=sku)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

        final_response = client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=messages,
            max_tokens=500,
        )

        return final_response.choices[0].message.content
