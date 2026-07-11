"""Per-user context graph (stage 4 + 10).

Every query and write is keyed by ``user_id`` — that id IS the partition, so one
person's recency / theme-fatigue / narrative arcs never touch another's. Each
surface carries a stable id for the same person (browser ``localStorage.resonate_uid``,
the extension's ``chrome.storage`` id handed over via ``?uid=``, or the MCP
``user_id`` argument), so the popup, the reels page and Ezra all deepen ONE graph.

Two interchangeable backends behind the same interface:

  LocalMemory  in-process dict + optional JSON snapshot. Thread-safe (the server
               is a ThreadingHTTPServer, so many users hit it at once). Perfect for
               the demo and single-node deploys.
  RedisMemory  the same graph as namespaced Redis keys (``resonate:events:<uid>``),
               so it survives restarts and scales across processes/instances. Used
               when RESONATE_MEMORY=redis + REDIS_URL are set; **auto-falls back to
               LocalMemory** if the package or server is unreachable, so a bad Redis
               URL can never take the product down.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import Counter


def _derive(events, recency_window, episodes):
    """Pure graph queries over a plain event list — shared by both backends so their
    behaviour is identical and unit-testable without any store."""
    recent = events[-recency_window:]

    def recency_penalty(reference):
        for i, e in enumerate(reversed(recent)):
            if e["reference"] == reference:
                return max(0.0, 1.0 - i / max(1, recency_window))
        return 0.0

    def theme_fatigue(themes):
        if not recent:
            return 0.0
        rc = Counter(t for e in recent for t in e["themes"])
        total = sum(rc.values()) or 1
        return sum(rc.get(t, 0) for t in themes) / total

    narr_counter = Counter(t for e in events for t in e["themes"])
    narrative_themes = [t for t, _ in narr_counter.most_common(3)]

    def narrative_continuity(themes):
        narr, ts = set(narrative_themes), set(themes)
        if not narr or not ts:
            return 0.0
        return len(narr & ts) / len(ts)

    return {
        "recency_penalty": recency_penalty,
        "theme_fatigue": theme_fatigue,
        "narrative_themes": narrative_themes,
        "narrative_continuity": narrative_continuity,
        "patterns": {"total_events": len(events), "episodes": episodes,
                     "top_themes": narr_counter.most_common(5)},
    }


class LocalMemory:
    backend = "local"

    def __init__(self, recency_window: int = 8, persist_path: str = None):
        self.recency_window = recency_window
        self.persist_path = persist_path
        self.events = {}      # user_id -> list[event dict]
        self._episode = {}    # user_id -> running episode counter
        self._lock = threading.RLock()  # ThreadingHTTPServer -> concurrent users
        if persist_path:
            self._load()

    # ---- writes (all under the lock; the file is rewritten atomically) ----
    def start_episode(self, user_id: str) -> int:
        with self._lock:
            self._episode[user_id] = self._episode.get(user_id, 0) + 1
            return self._episode[user_id]

    def add(self, user_id, themes, intensity, reference, episode=None):
        with self._lock:
            self.events.setdefault(user_id, []).append({
                "ts": time.time(),
                "themes": list(themes),
                "intensity": float(intensity),
                "reference": reference,
                "episode": episode or self._episode.get(user_id, 1),
            })
            if self.persist_path:
                self._save()

    # ---- reads (snapshot the per-user list under the lock, then compute) ----
    def _snapshot(self, user_id):
        with self._lock:
            return list(self.events.get(user_id, [])), self._episode.get(user_id, 0)

    def theme_count(self, user_id, theme) -> int:
        events, _ = self._snapshot(user_id)
        return sum(1 for e in events if theme in e["themes"])

    def recent(self, user_id) -> list:
        events, _ = self._snapshot(user_id)
        return events[-self.recency_window:]

    def recency_penalty(self, user_id, reference) -> float:
        events, _ = self._snapshot(user_id)
        return _derive(events, self.recency_window, 0)["recency_penalty"](reference)

    def theme_fatigue(self, user_id, themes) -> float:
        events, _ = self._snapshot(user_id)
        return _derive(events, self.recency_window, 0)["theme_fatigue"](themes)

    def narrative_themes(self, user_id, top: int = 3) -> list:
        events, _ = self._snapshot(user_id)
        return [t for t, _ in Counter(t for e in events for t in e["themes"]).most_common(top)]

    def narrative_continuity(self, user_id, themes) -> float:
        events, _ = self._snapshot(user_id)
        return _derive(events, self.recency_window, 0)["narrative_continuity"](themes)

    def patterns(self, user_id) -> dict:
        events, episodes = self._snapshot(user_id)
        return _derive(events, self.recency_window, episodes)["patterns"]

    # ---- persistence ----
    def _load(self):
        try:
            with open(self.persist_path, encoding="utf-8") as f:
                data = json.load(f)
            self.events = data.get("events", {})
            self._episode = data.get("episode", {})
        except (OSError, ValueError):
            pass

    def _save(self):
        try:
            tmp = self.persist_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"events": self.events, "episode": self._episode}, f)
            os.replace(tmp, self.persist_path)
        except OSError:
            pass


class RedisMemory:
    """Same context graph, stored as namespaced Redis keys so it survives restarts
    and is shared across every process/instance:

      resonate:episode:<user_id>  INCR counter   (episode ids)
      resonate:events:<user_id>   list of JSON    (the event log)

    Redis handles concurrency server-side, so no app-level lock is needed. Reads pull
    the per-user list (bounded by MAXLEN on write) and reuse the exact same derivations
    as LocalMemory, so behaviour is identical."""

    backend = "redis"
    MAXLEN = 500  # cap the per-user log so a heavy user can't grow unbounded

    def __init__(self, url: str, recency_window: int = 8, ttl_days: int = 0):
        import redis  # optional dep — ImportError => factory falls back to local
        self.recency_window = recency_window
        self.ttl = int(ttl_days * 86400) if ttl_days else 0
        self.r = redis.from_url(url, decode_responses=True, socket_connect_timeout=3)
        self.r.ping()  # unreachable => raises => factory falls back to local

    def _k(self, kind, user_id):
        return "resonate:%s:%s" % (kind, user_id)

    def start_episode(self, user_id: str) -> int:
        return int(self.r.incr(self._k("episode", user_id)))

    def add(self, user_id, themes, intensity, reference, episode=None):
        ep = episode or int(self.r.get(self._k("episode", user_id)) or 1)
        ev = json.dumps({"ts": time.time(), "themes": list(themes),
                         "intensity": float(intensity), "reference": reference, "episode": ep})
        key = self._k("events", user_id)
        pipe = self.r.pipeline()
        pipe.rpush(key, ev)
        pipe.ltrim(key, -self.MAXLEN, -1)
        if self.ttl:
            pipe.expire(key, self.ttl)
        pipe.execute()

    def _events(self, user_id):
        return [json.loads(e) for e in self.r.lrange(self._k("events", user_id), 0, -1)]

    def _episodes(self, user_id):
        return int(self.r.get(self._k("episode", user_id)) or 0)

    def theme_count(self, user_id, theme) -> int:
        return sum(1 for e in self._events(user_id) if theme in e["themes"])

    def recent(self, user_id) -> list:
        return self._events(user_id)[-self.recency_window:]

    def recency_penalty(self, user_id, reference) -> float:
        return _derive(self._events(user_id), self.recency_window, 0)["recency_penalty"](reference)

    def theme_fatigue(self, user_id, themes) -> float:
        return _derive(self._events(user_id), self.recency_window, 0)["theme_fatigue"](themes)

    def narrative_themes(self, user_id, top: int = 3) -> list:
        return [t for t, _ in Counter(t for e in self._events(user_id)
                                      for t in e["themes"]).most_common(top)]

    def narrative_continuity(self, user_id, themes) -> float:
        return _derive(self._events(user_id), self.recency_window, 0)["narrative_continuity"](themes)

    def patterns(self, user_id) -> dict:
        return _derive(self._events(user_id), self.recency_window,
                       self._episodes(user_id))["patterns"]


def make_memory(config):
    """Factory. RESONATE_MEMORY=redis + REDIS_URL -> RedisMemory (shared, multi-instance),
    auto-falling back to LocalMemory if the redis package or server is unavailable so a bad
    URL can never break the product. Local persists to disk only when memory_persist is set,
    so tests/eval/demo stay deterministic."""
    path = config.memory_path if getattr(config, "memory_persist", False) else None
    if getattr(config, "memory_backend", "local") == "redis" and getattr(config, "redis_url", ""):
        try:
            mem = RedisMemory(config.redis_url, recency_window=config.recency_window)
            import sys
            sys.stderr.write("resonate-memory: redis backend active\n")
            return mem
        except Exception as e:  # ImportError, ConnectionError, timeout — degrade, don't die
            import sys
            sys.stderr.write("resonate-memory: redis unavailable (%s) -> local fallback\n"
                             % str(e)[:120])
    return LocalMemory(recency_window=config.recency_window, persist_path=path)
