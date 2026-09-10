import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status


class RateLimiter:
    """In-memory sliding window rate limiter per client IP. Can be swapped with Redis for distributed environments."""

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        self.requests: Dict[str, list[float]] = {}

    def check_rate_limit(self, client_id: str) -> None:
        now = time.time()
        cutoff = now - self.window_seconds
        client_timestamps = [t for t in self.requests.get(client_id, []) if t > cutoff]

        if len(client_timestamps) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Too many requests to AI endpoints.",
            )

        client_timestamps.append(now)
        self.requests[client_id] = client_timestamps


rate_limiter = RateLimiter(requests_per_minute=60)


async def ai_rate_limit_middleware(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter.check_rate_limit(client_ip)
