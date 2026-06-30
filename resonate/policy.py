"""Delivery Policy — the "non-annoying" brain.

Separates WHEN/WHETHER to surface a verse from WHICH verse (the engine). The whole point of
the competition's "not a pop-up, not an afterthought" is restraint: Scripture as earned
punctuation at the *seams* of an experience (a finished lesson, a real struggle, a milestone,
a deliberate pause), never an interruption mid-flow. Silence is the default.

Rules enforced here:
  - Seam-timed   : only fire on natural boundary events, never mid-activity.
  - Confident    : stay silent unless the match is strong enough.
  - Rare         : cooldown between surfaces + a hard per-session cap.
  - Learns       : a dismissal makes it back off that theme for a while.
  - Manual always: if the person explicitly asks, honour it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

# Natural "seams" where a verse may surface. Anything else is treated as mid-flow -> silence.
DEFAULT_SEAMS = {"lesson_complete", "struggle", "streak", "session_end", "pause", "reflect"}


@dataclass
class PolicyConfig:
    seams: set = field(default_factory=lambda: set(DEFAULT_SEAMS))
    min_confidence: float = 0.55
    cooldown_seconds: float = 90.0   # rare = precious
    max_per_session: int = 3
    dismiss_backoff: int = 5          # suppress a dismissed theme for N subsequent decisions


@dataclass
class _UserState:
    last_surface_ts: float = float("-inf")  # no prior surface -> first one is never blocked by cooldown
    session_count: int = 0
    decisions: int = 0
    dismissed: dict = field(default_factory=dict)  # theme -> decision-index until which suppressed


class DeliveryPolicy:
    def __init__(self, config: PolicyConfig = None, clock=time.time):
        self.cfg = config or PolicyConfig()
        self.clock = clock
        self.users = {}

    def _u(self, user_id):
        return self.users.setdefault(user_id, _UserState())

    def reset_session(self, user_id):
        self._u(user_id).session_count = 0

    def decide(self, user_id, event, confidence=None, themes=(), now=None, manual=False):
        """Return {'surface': bool, 'reason': str}."""
        u = self._u(user_id)
        u.decisions += 1
        now = self.clock() if now is None else now

        if manual or event == "manual":
            return self._allow(u, now, "manual request")
        if event not in self.cfg.seams:
            return self._deny("not a seam — would interrupt flow")
        if u.session_count >= self.cfg.max_per_session:
            return self._deny("session cap reached")
        if now - u.last_surface_ts < self.cfg.cooldown_seconds:
            return self._deny("within cooldown")
        if confidence is not None and confidence < self.cfg.min_confidence:
            return self._deny("confidence below threshold")
        for t in themes:
            if u.dismissed.get(t, 0) >= u.decisions:
                return self._deny("theme recently dismissed")
        return self._allow(u, now, "seam, confident, within budget")

    def record_dismiss(self, user_id, themes):
        u = self._u(user_id)
        for t in themes:
            u.dismissed[t] = u.decisions + self.cfg.dismiss_backoff

    def _allow(self, u, now, reason):
        u.last_surface_ts = now
        u.session_count += 1
        return {"surface": True, "reason": reason}

    @staticmethod
    def _deny(reason):
        return {"surface": False, "reason": reason}
