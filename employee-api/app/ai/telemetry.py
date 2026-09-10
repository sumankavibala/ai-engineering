import logging
from dataclasses import dataclass, field
from typing import Dict, Any
from app.ai.context import get_request_id
from app.ai.cost import cost_calculator

logger = logging.getLogger(__name__)


@dataclass
class TelemetryMetrics:
    request_id: str = ""
    llm_calls: int = 0
    tool_calls: int = 0
    retrieval_calls: int = 0
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    status: str = "success"
    total_cost: float = 0.0
    latency_breakdown: Dict[str, float] = field(default_factory=dict)

    def add_llm_call(self, model: str, usage: Dict[str, Any] | None, latency_ms: float):
        self.llm_calls += 1
        if usage:
            inp = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            out = usage.get("completion_tokens") or usage.get("output_tokens") or 0
            self.input_tokens += inp
            self.output_tokens += out
            self.total_cost += cost_calculator.calculate(
                model, {"input_tokens": inp, "output_tokens": out}
            )
        self.latency_breakdown[f"llm_{self.llm_calls}"] = round(latency_ms, 2)

    def add_tool_call(self, tool_name: str, latency_ms: float):
        self.tool_calls += 1
        self.latency_breakdown[f"tool_{tool_name}"] = round(latency_ms, 2)

    def add_retrieval_call(self, latency_ms: float):
        self.retrieval_calls += 1
        self.latency_breakdown[f"retrieval_{self.retrieval_calls}"] = round(latency_ms, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id or get_request_id() or "unknown",
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "retrieval_calls": self.retrieval_calls,
            "latency_ms": round(self.latency_ms, 2),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "status": self.status,
            "latency_breakdown": self.latency_breakdown,
        }

    def log_summary(self):
        telemetry_dict = self.to_dict()
        logger.info("agent_telemetry_summary", extra={"telemetry": telemetry_dict})
        return telemetry_dict
