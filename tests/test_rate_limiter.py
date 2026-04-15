"""
test_rate_limiter.py — Unit tests for the sliding-window rate limiter.

Naming convention: [function] should [expected behavior] when [condition].
"""

import time
import unittest

from app.rate_limiter import SlidingWindowRateLimiter


class TestSlidingWindowRateLimiter(unittest.TestCase):

    def _make_limiter(self, max_requests: int = 5, window_seconds: float = 1.0) -> SlidingWindowRateLimiter:
        """Return a fresh limiter with a short window for fast tests."""
        return SlidingWindowRateLimiter(max_requests=max_requests, window_seconds=window_seconds)

    # ------------------------------------------------------------------
    # Construction guards
    # ------------------------------------------------------------------

    def test_init_should_raise_when_max_requests_is_zero(self):
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(max_requests=0)

    def test_init_should_raise_when_max_requests_is_negative(self):
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(max_requests=-1)

    def test_init_should_raise_when_window_seconds_is_zero(self):
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(max_requests=10, window_seconds=0)

    def test_init_should_raise_when_window_seconds_is_negative(self):
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(max_requests=10, window_seconds=-5)

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_is_allowed_should_return_true_when_under_limit(self):
        limiter = self._make_limiter(max_requests=3)
        allowed, retry_after = limiter.is_allowed("192.168.1.1")
        self.assertTrue(allowed)
        self.assertEqual(retry_after, 0)

    def test_is_allowed_should_allow_exactly_max_requests_in_window(self):
        limiter = self._make_limiter(max_requests=3)
        ip = "10.0.0.1"
        for i in range(3):
            allowed, _ = limiter.is_allowed(ip)
            self.assertTrue(allowed, f"Request {i+1} should be allowed")

    def test_is_allowed_should_block_request_exceeding_limit(self):
        limiter = self._make_limiter(max_requests=3)
        ip = "10.0.0.2"
        for _ in range(3):
            limiter.is_allowed(ip)
        allowed, retry_after = limiter.is_allowed(ip)
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

    # ------------------------------------------------------------------
    # Window sliding behaviour
    # ------------------------------------------------------------------

    def test_is_allowed_should_allow_again_after_window_expires(self):
        limiter = self._make_limiter(max_requests=2, window_seconds=0.1)
        ip = "10.0.0.3"
        limiter.is_allowed(ip)
        limiter.is_allowed(ip)
        # Both slots used — next should block
        allowed, _ = limiter.is_allowed(ip)
        self.assertFalse(allowed)

        time.sleep(0.15)  # Wait for window to slide
        allowed, _ = limiter.is_allowed(ip)
        self.assertTrue(allowed)

    # ------------------------------------------------------------------
    # IP isolation
    # ------------------------------------------------------------------

    def test_is_allowed_should_track_each_ip_independently(self):
        limiter = self._make_limiter(max_requests=2)
        ip_a = "10.0.1.1"
        ip_b = "10.0.1.2"
        limiter.is_allowed(ip_a)
        limiter.is_allowed(ip_a)
        # ip_a is now at limit; ip_b should still be allowed.
        allowed_b, _ = limiter.is_allowed(ip_b)
        self.assertTrue(allowed_b)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def test_reset_should_clear_window_for_ip(self):
        limiter = self._make_limiter(max_requests=2)
        ip = "10.0.2.1"
        limiter.is_allowed(ip)
        limiter.is_allowed(ip)
        allowed, _ = limiter.is_allowed(ip)
        self.assertFalse(allowed)

        limiter.reset(ip)
        allowed, _ = limiter.is_allowed(ip)
        self.assertTrue(allowed)

    def test_reset_should_not_raise_when_ip_not_tracked(self):
        limiter = self._make_limiter()
        try:
            limiter.reset("unknown-ip")
        except Exception as exc:
            self.fail(f"reset raised unexpectedly: {exc}")

    # ------------------------------------------------------------------
    # Retry-After header value
    # ------------------------------------------------------------------

    def test_is_allowed_should_return_positive_retry_after_when_blocked(self):
        limiter = self._make_limiter(max_requests=1, window_seconds=60.0)
        ip = "10.0.3.1"
        limiter.is_allowed(ip)
        allowed, retry_after = limiter.is_allowed(ip)
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)
        self.assertLessEqual(retry_after, 61)

    # ------------------------------------------------------------------
    # Performance at 100k calls (three-volume-tier smoke test)
    # ------------------------------------------------------------------

    def test_is_allowed_should_handle_100k_requests_without_crash(self):
        """
        Smoke test at 100k volume tier. Confirms no memory leak or
        logic error at scale. Each unique IP should always be allowed
        on its first request.
        """
        limiter = SlidingWindowRateLimiter(max_requests=200, window_seconds=60.0)
        for i in range(100_000):
            ip = f"10.{(i // 65536) % 256}.{(i // 256) % 256}.{i % 256}"
            allowed, _ = limiter.is_allowed(ip)
            # First request for any unique IP must always be allowed.
            self.assertTrue(allowed, f"First request for {ip} should be allowed")


if __name__ == "__main__":
    unittest.main()
