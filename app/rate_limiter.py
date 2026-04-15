"""
rate_limiter.py — Sliding-window rate limiter keyed per client IP.

Analogy: imagine a turnstile that lets you through at most N times per minute.
Each time you push it, the oldest push from the window falls off the back.
If the window is full, you are blocked until a slot opens.
"""

import time
import threading
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """
    Thread-safe sliding-window counter: at most `max_requests` per `window_seconds` per IP.

    Time complexity per check: O(k) where k is the number of timestamps in the window —
    bounded by max_requests, so effectively O(1) at steady state.
    """

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0) -> None:
        """Configure the limiter with a request cap and rolling time window."""
        if max_requests < 1:
            raise ValueError("max_requests must be at least 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self._max_requests = max_requests
        self._window_seconds = window_seconds
        # deque per IP holds the monotonic timestamps of each allowed request.
        self._ip_windows: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> tuple[bool, int]:
        """
        Check whether a request from client_ip is within the rate limit.

        Returns (is_allowed, retry_after_seconds). retry_after_seconds is 0
        when the request is allowed.
        """
        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            window = self._ip_windows[client_ip]

            # Drop timestamps that have slid out of the window.
            while window and window[0] <= cutoff:
                window.popleft()

            if len(window) >= self._max_requests:
                # Earliest slot opens when the oldest request exits the window.
                retry_after = int(self._window_seconds - (now - window[0])) + 1
                return False, retry_after

            window.append(now)
            return True, 0

    def reset(self, client_ip: str) -> None:
        """Clear the window for a specific IP — useful in tests."""
        with self._lock:
            self._ip_windows.pop(client_ip, None)


# Module-level singleton; window parameters are overridden from env vars in main.py.
_limiter = SlidingWindowRateLimiter(max_requests=60, window_seconds=60.0)


def configure_limiter(max_requests: int, window_seconds: float) -> None:
    """Replace the module-level limiter with updated parameters."""
    global _limiter
    _limiter = SlidingWindowRateLimiter(max_requests=max_requests, window_seconds=window_seconds)


def get_client_ip(request: Request) -> str:
    """Extract the real client IP, respecting X-Forwarded-For when behind a proxy."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Only trust the first address in the chain.
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(request: Request) -> None:
    """
    FastAPI dependency that blocks requests exceeding the per-IP rate limit.

    Raises HTTP 429 with a Retry-After header when the limit is breached.
    Inject this into any route that must be rate-limited.
    """
    client_ip = get_client_ip(request)
    allowed, retry_after = _limiter.is_allowed(client_ip)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
            headers={"Retry-After": str(retry_after)},
        )
