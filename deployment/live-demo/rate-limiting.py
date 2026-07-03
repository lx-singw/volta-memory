"""Basic rate limiting for the public live demo instance."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque


class RateLimiter:
    def __init__(self, max_requests: int | None = None, window_seconds: int = 3600):
        self.max_requests = max_requests or int(os.environ.get("LIVE_DEMO_RATE_LIMIT_PER_IP", "20"))
        self.window_seconds = window_seconds
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, client_ip: str) -> bool:
        now = time.time()
        hits = self._hits[client_ip]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True


def demo_entity_reset_hours() -> int:
    return int(os.environ.get("LIVE_DEMO_DEMO_ENTITY_RESET_HOURS", "24"))
