"""Per-user rate limiting — the 'many people, one engine' guard.

Context graphs are already isolated per user_id (memory.py keys everything by it);
what a shared live engine additionally needs is fairness: one noisy user must not
drain the Gloo credit, monopolize the single Kokoro worker, or starve everyone
else. Sliding windows per (bucket, user) — tiny, in-memory, thread-safe. When a
deployment outgrows one process, the same keys move to Redis INCR/EXPIRE (the
memory backend has the identical upgrade path).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, rules: dict):
        """rules: {bucket: (max_hits, window_seconds)}"""
        self.rules = dict(rules)
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, bucket: str, key: str) -> bool:
        limit, window = self.rules[bucket]
        now = time.time()
        with self._lock:
            dq = self._hits[(bucket, key)]
            while dq and dq[0] <= now - window:
                dq.popleft()
            if len(dq) >= limit:
                return False
            dq.append(now)
            return True

    def retry_after(self, bucket: str, key: str) -> int:
        """Seconds until the oldest hit ages out — honest Retry-After for a 429."""
        _, window = self.rules[bucket]
        with self._lock:
            dq = self._hits[(bucket, key)]
            if not dq:
                return 0
            return max(0, int(dq[0] + window - time.time()) + 1)
