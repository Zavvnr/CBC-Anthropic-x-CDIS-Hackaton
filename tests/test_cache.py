"""
test_cache.py — Unit tests for the TTL LRU cache.

Naming convention: [function] should [expected behavior] when [condition].
"""

import time
import unittest

from app.cache import MISSING, TTLLRUCache


class TestTTLLRUCache(unittest.TestCase):

    def _make_cache(self, max_size: int = 4, ttl_seconds: float = 60.0) -> TTLLRUCache:
        """Return a small cache suitable for unit tests."""
        return TTLLRUCache(max_size=max_size, ttl_seconds=ttl_seconds)

    # ------------------------------------------------------------------
    # Construction guards
    # ------------------------------------------------------------------

    def test_init_should_raise_when_max_size_is_zero(self):
        with self.assertRaises(ValueError):
            TTLLRUCache(max_size=0)

    def test_init_should_raise_when_ttl_seconds_is_zero(self):
        with self.assertRaises(ValueError):
            TTLLRUCache(ttl_seconds=0)

    def test_init_should_raise_when_ttl_seconds_is_negative(self):
        with self.assertRaises(ValueError):
            TTLLRUCache(ttl_seconds=-1.0)

    # ------------------------------------------------------------------
    # Basic get / set
    # ------------------------------------------------------------------

    def test_get_should_return_missing_when_key_not_present(self):
        cache = self._make_cache()
        self.assertIs(cache.get("nonexistent"), MISSING)

    def test_set_should_store_value_retrievable_by_get(self):
        cache = self._make_cache()
        cache.set("hello", "world")
        self.assertEqual(cache.get("hello"), "world")

    def test_get_should_return_none_when_cached_value_is_none(self):
        cache = self._make_cache()
        cache.set("key", None)
        result = cache.get("key")
        # None is a valid cached value — should NOT be MISSING.
        self.assertIsNot(result, MISSING)
        self.assertIsNone(result)

    def test_set_should_overwrite_existing_key(self):
        cache = self._make_cache()
        cache.set("k", "first")
        cache.set("k", "second")
        self.assertEqual(cache.get("k"), "second")

    # ------------------------------------------------------------------
    # TTL expiry
    # ------------------------------------------------------------------

    def test_get_should_return_missing_when_entry_has_expired(self):
        cache = TTLLRUCache(max_size=4, ttl_seconds=0.05)
        cache.set("x", 42)
        time.sleep(0.1)
        self.assertIs(cache.get("x"), MISSING)

    def test_get_should_return_value_before_ttl_expires(self):
        cache = TTLLRUCache(max_size=4, ttl_seconds=1.0)
        cache.set("y", 99)
        self.assertEqual(cache.get("y"), 99)

    # ------------------------------------------------------------------
    # LRU eviction
    # ------------------------------------------------------------------

    def test_set_should_evict_lru_entry_when_at_capacity(self):
        cache = self._make_cache(max_size=2)
        cache.set("a", 1)
        cache.set("b", 2)
        # Access "a" to promote it; "b" becomes LRU.
        cache.get("a")
        cache.set("c", 3)  # Should evict "b"
        self.assertIs(cache.get("b"), MISSING)
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("c"), 3)

    def test_set_should_evict_oldest_entry_when_none_accessed(self):
        cache = self._make_cache(max_size=2)
        cache.set("first", 1)
        cache.set("second", 2)
        cache.set("third", 3)  # Should evict "first"
        self.assertIs(cache.get("first"), MISSING)

    # ------------------------------------------------------------------
    # Invalidate & clear
    # ------------------------------------------------------------------

    def test_invalidate_should_remove_specific_key(self):
        cache = self._make_cache()
        cache.set("alpha", "A")
        cache.set("beta", "B")
        cache.invalidate("alpha")
        self.assertIs(cache.get("alpha"), MISSING)
        self.assertEqual(cache.get("beta"), "B")

    def test_invalidate_should_not_raise_when_key_absent(self):
        cache = self._make_cache()
        try:
            cache.invalidate("ghost")
        except Exception as exc:
            self.fail(f"invalidate raised unexpectedly: {exc}")

    def test_clear_should_remove_all_entries(self):
        cache = self._make_cache()
        cache.set("p", 1)
        cache.set("q", 2)
        cache.clear()
        self.assertEqual(len(cache), 0)

    # ------------------------------------------------------------------
    # __len__
    # ------------------------------------------------------------------

    def test_len_should_return_number_of_unexpired_entries(self):
        cache = TTLLRUCache(max_size=10, ttl_seconds=0.05)
        cache.set("one", 1)
        cache.set("two", 2)
        self.assertEqual(len(cache), 2)
        time.sleep(0.1)
        self.assertEqual(len(cache), 0)

    # ------------------------------------------------------------------
    # Thread safety smoke test
    # ------------------------------------------------------------------

    def test_set_and_get_should_be_consistent_under_concurrent_access(self):
        """Smoke-test thread safety: concurrent writes should not corrupt state."""
        import threading
        cache = TTLLRUCache(max_size=256, ttl_seconds=5.0)
        errors: list = []

        def writer(thread_id: int) -> None:
            try:
                for i in range(100):
                    cache.set(f"key-{thread_id}-{i}", thread_id * 1000 + i)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [], f"Thread errors: {errors}")


if __name__ == "__main__":
    unittest.main()
