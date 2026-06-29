"""Per-user context graph (stage 4 + 10) — local backend.

Stored as a timestamped event log; the graph queries (recency, theme-fatigue, narrative
continuity, series patterns) are derived from it. A Redis backend with this same interface
lands in Phase 2/3 (vector index + episodic memory + semantic cache), auto-falling back to
this local store if Redis is unavailable.
"""
from __future__ import annotations

import time
from collections import Counter


class LocalMemory:
    backend = "local"

    def __init__(self, recency_window: int = 8):
        self.recency_window = recency_window
        self.events = {}      # user_id -> list[event dict]
        self._episode = {}    # user_id -> running episode counter

    def start_episode(self, user_id: str) -> int:
        self._episode[user_id] = self._episode.get(user_id, 0) + 1
        return self._episode[user_id]

    def add(self, user_id, themes, intensity, reference, episode=None):
        self.events.setdefault(user_id, []).append({
            "ts": time.time(),
            "themes": list(themes),
            "intensity": float(intensity),
            "reference": reference,
            "episode": episode or self._episode.get(user_id, 1),
        })

    def recent(self, user_id) -> list:
        return self.events.get(user_id, [])[-self.recency_window:]

    def recency_penalty(self, user_id, reference) -> float:
        """1.0 for the most recent delivery of this verse, decaying to 0 across the window."""
        recent = self.recent(user_id)
        for i, e in enumerate(reversed(recent)):
            if e["reference"] == reference:
                return max(0.0, 1.0 - i / max(1, self.recency_window))
        return 0.0

    def theme_fatigue(self, user_id, themes) -> float:
        """Share of recent beats that touched any of these themes (0..1)."""
        recent = self.recent(user_id)
        if not recent:
            return 0.0
        rc = Counter(t for e in recent for t in e["themes"])
        total = sum(rc.values()) or 1
        return sum(rc.get(t, 0) for t in themes) / total

    def narrative_themes(self, user_id, top: int = 3) -> list:
        c = Counter(t for e in self.events.get(user_id, []) for t in e["themes"])
        return [t for t, _ in c.most_common(top)]

    def narrative_continuity(self, user_id, themes) -> float:
        narr, ts = set(self.narrative_themes(user_id)), set(themes)
        if not narr or not ts:
            return 0.0
        return len(narr & ts) / len(ts)

    def patterns(self, user_id) -> dict:
        ev = self.events.get(user_id, [])
        c = Counter(t for e in ev for t in e["themes"])
        return {
            "total_events": len(ev),
            "episodes": self._episode.get(user_id, 0),
            "top_themes": c.most_common(5),
        }


def make_memory(config):
    """Factory. Phase 2/3 adds: if config.memory_backend == 'redis', try RedisMemory and fall
    back to LocalMemory on any connection error."""
    return LocalMemory(recency_window=config.recency_window)
