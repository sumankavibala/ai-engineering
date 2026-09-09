import json
import logging
import re
import time

from app.ai.client import client
from app.ai.logging_utils import log_token_usage
from app.ai.retry import call_with_retry
from app.ai.tools import INVENTORY_TOOL, POLICY_SEARCH_TOOL, ORDER_STATUS_TOOL

logger = logging.getLogger(__name__)


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

        response = call_with_retry(
            lambda: client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=messages,
                tools=[INVENTORY_TOOL, POLICY_SEARCH_TOOL, ORDER_STATUS_TOOL],
                max_tokens=500,
            )
        )

        elapsed = time.perf_counter() - start
        if getattr(response, "usage", None):
            log_token_usage(response.usage)

        logger.info(
            "llm_call",
            extra={
                "llm_latency": elapsed,
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

            tool_start = time.perf_counter()
            if name == "get_inventory":
                sku = arguments.get("sku")
                result = await self.inventory_service.get_inventory(sku=sku)
            elif name == "search_warehouse_policy":
                query = arguments.get("query")
                result = await self.rag_service.ask(question=query)
            elif name == "get_order_status":
                order_id = arguments.get("order_id")
                if self.order_service:
                    result = await self.order_service.get_order_status(order_id=order_id)
                else:
                    result = {"error": "Order service unavailable"}
            else:
                result = {"error": f"Unknown tool: {name}"}

            tool_elapsed = time.perf_counter() - tool_start
            logger.info(
                "tool_call",
                extra={
                    "tool": name,
                    "tool_latency": tool_elapsed,
                    "latency_seconds": tool_elapsed
                }
            )

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

        start = time.perf_counter()

        final_response = call_with_retry(
            lambda: client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=messages,
                max_tokens=1000,
            )
        )

        elapsed = time.perf_counter() - start
        if getattr(final_response, "usage", None):
            log_token_usage(final_response.usage)

        logger.info(
            "llm_call",
            extra={
                "llm_latency": elapsed,
                "latency_seconds": elapsed
            }
        )

        return strip_thinking_tags(final_response.choices[0].message.content)

    async def ask_stream(self, question: str):
        messages = [{"role": "user", "content": question}]

        start = time.perf_counter()
        response = call_with_retry(
            lambda: client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=messages,
                tools=[INVENTORY_TOOL, POLICY_SEARCH_TOOL, ORDER_STATUS_TOOL],
                max_tokens=500,
            )
        )
        elapsed = time.perf_counter() - start
        if getattr(response, "usage", None):
            log_token_usage(response.usage)
        logger.info("llm_call", extra={"llm_latency": elapsed, "latency_seconds": elapsed})

        message = response.choices[0].message

        if not message.tool_calls:
            start = time.perf_counter()
            stream_response = call_with_retry(
                lambda: client.chat.completions.create(
                    model="qwen/qwen3.6-27b",
                    messages=messages,
                    max_tokens=1000,
                    stream=True,
                    stream_options={"include_usage": True},
                )
            )
            in_think_block = False
            buffer = ""
            for chunk in stream_response:
                if getattr(chunk, "usage", None):
                    log_token_usage(chunk.usage)
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta.content or ""
                if not delta:
                    continue
                buffer += delta
                while buffer:
                    if not in_think_block:
                        think_start = buffer.find("<think>")
                        if think_start != -1:
                            if think_start > 0:
                                yield buffer[:think_start]
                            buffer = buffer[think_start + 7 :]
                            in_think_block = True
                        else:
                            if any("<think>"[:i] == buffer[-i:] for i in range(1, len("<think>"))):
                                break
                            yield buffer
                            buffer = ""
                    else:
                        think_end = buffer.find("</think>")
                        if think_end != -1:
                            buffer = buffer[think_end + 8 :]
                            in_think_block = False
                        else:
                            buffer = ""
                            break
            if buffer and not in_think_block:
                yield buffer
            elapsed = time.perf_counter() - start
            logger.info("llm_call", extra={"llm_latency": elapsed, "latency_seconds": elapsed})
            return

        messages.append(message)

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            tool_start = time.perf_counter()
            if name == "get_inventory":
                sku = arguments.get("sku")
                result = await self.inventory_service.get_inventory(sku=sku)
            elif name == "search_warehouse_policy":
                query = arguments.get("query")
                result = await self.rag_service.ask(question=query)
            elif name == "get_order_status":
                order_id = arguments.get("order_id")
                if self.order_service:
                    result = await self.order_service.get_order_status(order_id=order_id)
                else:
                    result = {"error": "Order service unavailable"}
            else:
                result = {"error": f"Unknown tool: {name}"}

            tool_elapsed = time.perf_counter() - tool_start
            logger.info(
                "tool_call",
                extra={
                    "tool": name,
                    "tool_latency": tool_elapsed,
                    "latency_seconds": tool_elapsed
                }
            )

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

        start = time.perf_counter()
        final_stream = call_with_retry(
            lambda: client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=messages,
                max_tokens=1000,
                stream=True,
                stream_options={"include_usage": True},
            )
        )

        in_think_block = False
        buffer = ""
        for chunk in final_stream:
            if getattr(chunk, "usage", None):
                log_token_usage(chunk.usage)
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta.content or ""
            if not delta:
                continue
            buffer += delta
            while buffer:
                if not in_think_block:
                    think_start = buffer.find("<think>")
                    if think_start != -1:
                        if think_start > 0:
                            yield buffer[:think_start]
                        buffer = buffer[think_start + 7 :]
                        in_think_block = True
                    else:
                        if any("<think>"[:i] == buffer[-i:] for i in range(1, len("<think>"))):
                            break
                        yield buffer
                        buffer = ""
                else:
                    think_end = buffer.find("</think>")
                    if think_end != -1:
                        buffer = buffer[think_end + 8 :]
                        in_think_block = False
                    else:
                        buffer = ""
                        break

        if buffer and not in_think_block:
            yield buffer

        elapsed = time.perf_counter() - start
        logger.info("llm_call", extra={"llm_latency": elapsed, "latency_seconds": elapsed})

