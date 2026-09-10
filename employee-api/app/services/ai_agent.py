import json
import logging
import re
from app.ai.client import client
from app.ai.logging_utils import log_token_usage
from app.ai.retry import call_with_retry
from app.ai.tools import INVENTORY_TOOL, POLICY_SEARCH_TOOL, ORDER_STATUS_TOOL
from app.ai.timer import Timer
from app.ai.telemetry import TelemetryMetrics

logger = logging.getLogger(__name__)


def strip_thinking_tags(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL)
    return text.strip()


class AIAgentService:
    def __init__(self, inventory_service, rag_service, order_service=None):
        self.inventory_service = inventory_service
        self.rag_service = rag_service
        self.order_service = order_service

    async def ask(self, question: str):
        telemetry = TelemetryMetrics()
        with Timer() as req_timer:
            messages = [{"role": "user", "content": question}]

            with Timer() as llm1_timer:
                response = call_with_retry(
                    lambda: client.chat.completions.create(
                        model="qwen/qwen3.6-27b",
                        messages=messages,
                        tools=[INVENTORY_TOOL, POLICY_SEARCH_TOOL, ORDER_STATUS_TOOL],
                        max_tokens=500,
                    )
                )

            usage = getattr(response, "usage", None)
            if usage:
                log_token_usage(usage)
                telemetry.add_llm_call(
                    "qwen/qwen3.6-27b",
                    usage.__dict__ if hasattr(usage, "__dict__") else None,
                    llm1_timer.elapsed_ms,
                )
            else:
                telemetry.add_llm_call("qwen/qwen3.6-27b", None, llm1_timer.elapsed_ms)

            logger.info("llm_call", extra={"llm_latency": llm1_timer.elapsed_ms / 1000.0})

            message = response.choices[0].message

            if not message.tool_calls:
                telemetry.latency_ms = req_timer.elapsed_ms
                telemetry.log_summary()
                return strip_thinking_tags(message.content)

            messages.append(message)

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                with Timer() as tool_timer:
                    if name == "get_inventory":
                        sku = arguments.get("sku")
                        result = await self.inventory_service.get_inventory(sku=sku)
                    elif name == "search_warehouse_policy":
                        query = arguments.get("query")
                        result = await self.rag_service.ask(question=query, telemetry=telemetry)
                    elif name == "get_order_status":
                        order_id = arguments.get("order_id")
                        if self.order_service:
                            result = await self.order_service.get_order_status(order_id=order_id)
                        else:
                            result = {"error": "Order service unavailable"}
                    else:
                        result = {"error": f"Unknown tool: {name}"}

                telemetry.add_tool_call(name, tool_timer.elapsed_ms)
                logger.info(
                    "tool_call",
                    extra={"tool": name, "tool_latency": tool_timer.elapsed_ms / 1000.0},
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

            with Timer() as llm2_timer:
                final_response = call_with_retry(
                    lambda: client.chat.completions.create(
                        model="qwen/qwen3.6-27b",
                        messages=messages,
                        max_tokens=1000,
                    )
                )

            final_usage = getattr(final_response, "usage", None)
            if final_usage:
                log_token_usage(final_usage)
                telemetry.add_llm_call(
                    "qwen/qwen3.6-27b",
                    final_usage.__dict__ if hasattr(final_usage, "__dict__") else None,
                    llm2_timer.elapsed_ms,
                )
            else:
                telemetry.add_llm_call("qwen/qwen3.6-27b", None, llm2_timer.elapsed_ms)

            logger.info("llm_call", extra={"llm_latency": llm2_timer.elapsed_ms / 1000.0})

        telemetry.latency_ms = req_timer.elapsed_ms
        telemetry.log_summary()
        return strip_thinking_tags(final_response.choices[0].message.content)

    async def ask_stream(self, question: str):
        telemetry = TelemetryMetrics()
        with Timer() as req_timer:
            messages = [{"role": "user", "content": question}]

            with Timer() as llm1_timer:
                response = call_with_retry(
                    lambda: client.chat.completions.create(
                        model="qwen/qwen3.6-27b",
                        messages=messages,
                        tools=[INVENTORY_TOOL, POLICY_SEARCH_TOOL, ORDER_STATUS_TOOL],
                        max_tokens=500,
                    )
                )

            usage = getattr(response, "usage", None)
            if usage:
                log_token_usage(usage)
                telemetry.add_llm_call("qwen/qwen3.6-27b", usage.__dict__ if hasattr(usage, "__dict__") else None, llm1_timer.elapsed_ms)
            else:
                telemetry.add_llm_call("qwen/qwen3.6-27b", None, llm1_timer.elapsed_ms)

            logger.info("llm_call", extra={"llm_latency": llm1_timer.elapsed_ms / 1000.0})

            message = response.choices[0].message

            if not message.tool_calls:
                with Timer() as stream_timer:
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
                        c_usage = getattr(chunk, "usage", None)
                        if c_usage:
                            log_token_usage(c_usage)
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

                telemetry.latency_ms = req_timer.elapsed_ms
                telemetry.log_summary()
                return

            messages.append(message)

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                with Timer() as tool_timer:
                    if name == "get_inventory":
                        sku = arguments.get("sku")
                        result = await self.inventory_service.get_inventory(sku=sku)
                    elif name == "search_warehouse_policy":
                        query = arguments.get("query")
                        result = await self.rag_service.ask(question=query, telemetry=telemetry)
                    elif name == "get_order_status":
                        order_id = arguments.get("order_id")
                        if self.order_service:
                            result = await self.order_service.get_order_status(order_id=order_id)
                        else:
                            result = {"error": "Order service unavailable"}
                    else:
                        result = {"error": f"Unknown tool: {name}"}

                telemetry.add_tool_call(name, tool_timer.elapsed_ms)
                logger.info(
                    "tool_call",
                    extra={"tool": name, "tool_latency": tool_timer.elapsed_ms / 1000.0},
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

            with Timer() as stream_timer:
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
                    c_usage = getattr(chunk, "usage", None)
                    if c_usage:
                        log_token_usage(c_usage)
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

        telemetry.latency_ms = req_timer.elapsed_ms
        telemetry.log_summary()
