from __future__ import annotations

import threading
import time


class RateLimiter:
    """Simple per-source blocking rate limiter."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_request_at: dict[str, float] = {}

    def wait(self, source: str, min_interval_seconds: float) -> None:
        if min_interval_seconds <= 0:
            return
        with self._lock:
            now = time.monotonic()
            last = self._last_request_at.get(source)
            if last is not None:
                elapsed = now - last
                remaining = min_interval_seconds - elapsed
                if remaining > 0:
                    time.sleep(remaining)
            self._last_request_at[source] = time.monotonic()
