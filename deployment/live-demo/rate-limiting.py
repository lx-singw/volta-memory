"""Local policy fixture for the public edge.

Production throttling is configured at Alibaba Cloud API Gateway, where it can
be applied before Function Compute and Qwen are invoked. This helper remains
useful for local smoke tests; it never resets or shares a demo workspace.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque


class RateLimiter:
    def __init__(self, max_requests: int | None = None, window_seconds: int = 3600):
        self.max_requests = max_requests or int(os.environ.get("API_GATEWAY_RATE_LIMIT_PER_IP", "10"))
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
