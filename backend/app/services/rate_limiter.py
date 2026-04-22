from __future__ import annotations

import time
from collections import defaultdict, deque
from functools import lru_cache
from threading import Lock

from backend.app.core.config import get_settings


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        with self._lock:
            now = time.time()
            bucket = self._requests[key]
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return False
            bucket.append(now)
            return True


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    settings = get_settings()
    return RateLimiter(max_requests=settings.api_rate_limit)
