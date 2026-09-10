import time
from typing import Any, Dict, Optional


class PolicyCache:
    """In-memory cache for stable warehouse policy queries with TTL support."""

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _make_key(self, question: str, department: Optional[str] = None) -> str:
        key_str = f"{question.strip().lower()}:{department or 'all'}"
        return key_str

    def get(self, question: str, department: Optional[str] = None) -> Optional[Any]:
        key = self._make_key(question, department)
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            del self._cache[key]
            return None
        return entry["value"]

    def set(self, question: str, value: Any, department: Optional[str] = None) -> None:
        key = self._make_key(question, department)
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + self.ttl_seconds,
        }

    def clear(self) -> None:
        self._cache.clear()


policy_cache = PolicyCache(ttl_seconds=3600)
