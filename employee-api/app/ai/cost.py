from typing import Dict, Any


DEFAULT_PRICING = {
    # Rates per 1,000,000 tokens (USD)
    "qwen/qwen3.6-27b": {"input_per_1m": 0.30, "output_per_1m": 0.60},
    "openai/gpt-oss-120b": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    "gpt-4o": {"input_per_1m": 2.50, "output_per_1m": 10.00},
    "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    "default": {"input_per_1m": 0.20, "output_per_1m": 0.60},
}


class CostCalculator:
    def __init__(self, pricing_table: Dict[str, Dict[str, float]] | None = None):
        self.pricing_table = pricing_table or DEFAULT_PRICING

    def calculate(self, model: str, usage: Dict[str, Any]) -> float:
        model_pricing = self.pricing_table.get(model, self.pricing_table["default"])
        input_tokens = usage.get("input_tokens", 0) or 0
        output_tokens = usage.get("output_tokens", 0) or 0

        input_cost = (input_tokens / 1_000_000.0) * model_pricing.get("input_per_1m", 0.0)
        output_cost = (output_tokens / 1_000_000.0) * model_pricing.get("output_per_1m", 0.0)

        return round(input_cost + output_cost, 6)


cost_calculator = CostCalculator()
