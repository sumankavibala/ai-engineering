import pytest
from unittest.mock import MagicMock
from app.ai.timer import Timer
from app.ai.cost import CostCalculator
from app.ai.telemetry import TelemetryMetrics
from app.ai.cache import PolicyCache
from app.ai.rate_limiter import RateLimiter
from app.services.rag import rerank_chunks
from fastapi import HTTPException


def test_timer_sync():
    with Timer() as t:
        _ = 1 + 1
    assert t.elapsed_ms >= 0.0


@pytest.mark.anyio
async def test_timer_async():
    async with Timer() as t:
        _ = 1 + 1
    assert t.elapsed_ms >= 0.0


def test_cost_calculator():
    calc = CostCalculator()
    cost = calc.calculate("qwen/qwen3.6-27b", {"input_tokens": 1000, "output_tokens": 500})
    assert cost > 0.0
    # 1000/1M * 0.30 + 500/1M * 0.60 = 0.0003 + 0.0003 = 0.0006
    assert cost == 0.0006


def test_telemetry_metrics():
    metrics = TelemetryMetrics(request_id="req-123")
    metrics.add_llm_call("qwen/qwen3.6-27b", {"prompt_tokens": 100, "completion_tokens": 50}, 150.0)
    metrics.add_tool_call("get_inventory", 40.0)
    metrics.add_retrieval_call(30.0)
    metrics.latency_ms = 220.0

    data = metrics.to_dict()
    assert data["request_id"] == "req-123"
    assert data["llm_calls"] == 1
    assert data["tool_calls"] == 1
    assert data["retrieval_calls"] == 1
    assert data["input_tokens"] == 100
    assert data["output_tokens"] == 50
    assert data["total_tokens"] == 150
    assert data["status"] == "success"


def test_policy_cache():
    cache = PolicyCache(ttl_seconds=60)
    cache.set("What is the receiving policy?", {"answer": "Receiving procedure details"})

    res = cache.get("What is the receiving policy?")
    assert res == {"answer": "Receiving procedure details"}

    cache.clear()
    assert cache.get("What is the receiving policy?") is None


def test_rate_limiter():
    limiter = RateLimiter(requests_per_minute=2)
    client_ip = "127.0.0.1"

    limiter.check_rate_limit(client_ip)
    limiter.check_rate_limit(client_ip)

    with pytest.raises(HTTPException) as exc_info:
        limiter.check_rate_limit(client_ip)
    assert exc_info.value.status_code == 429


def test_rerank_chunks():
    chunk1 = MagicMock()
    chunk1.content = "Warehouse receiving procedures and docks"
    chunk2 = MagicMock()
    chunk2.content = "Employee cafeteria hours and food policy"

    results = [
        (chunk2, 0.20),
        (chunk1, 0.30),
    ]

    reranked = rerank_chunks("warehouse receiving procedure", results, max_keep=1)
    assert len(reranked) == 1
    # chunk1 has higher term match with 'warehouse receiving procedure'
    assert reranked[0][0] == chunk1
