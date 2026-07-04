"""Surface-agnostic responder — 'should we speak, and with what?'

Wraps the engine + Delivery Policy + a delivery target into one decision any connector
(Discord, wearable, a web widget, an MCP tool…) can act on, so each surface stays tiny.
"""
from __future__ import annotations

from .config import EngineConfig
from .engine import Engine
from .policy import DeliveryPolicy, PolicyConfig
from .delivery import TARGETS

_CHAT_SEAMS = {"message", "reflect", "lesson_complete", "struggle", "streak", "session_end", "pause"}


def default_policy():
    return DeliveryPolicy(PolicyConfig(seams=set(_CHAT_SEAMS), cooldown_seconds=3,
                                       max_per_session=50, min_confidence=0.5))


class Responder:
    def __init__(self, config=None, policy=None, target="discord"):
        self.engine = Engine(config or EngineConfig())
        self.policy = policy or default_policy()
        self.target = target

    def respond(self, user_id, text, event="message", history=None) -> dict:
        """Return a small decision dict:
          {surface: False, kind: 'silent', reason}                       — say nothing
          {surface: True,  kind: 'help', text}                           — crisis: point to help
          {surface: True,  kind: 'verse', delivery, rendered, memory_note}
        history: optional prior user messages — sharpens verse choice (see Engine.resonate).
        """
        result = self.engine.resonate(text, user_id, history=history)
        deliveries = result["deliveries"]

        held = next((d for d in deliveries if d["status"] == "safety_hold"), None)
        if held:
            return {"surface": True, "kind": "help", "text": held["message"]}

        delivered = [d for d in deliveries if d["status"] == "delivered"]
        if not delivered:
            return {"surface": False, "kind": "silent", "reason": "no resonant beat"}

        d = delivered[0]
        decision = self.policy.decide(user_id, event, confidence=d["confidence"], themes=d["beat"]["themes"])
        if not decision["surface"]:
            return {"surface": False, "kind": "silent", "reason": decision["reason"]}

        rendered = TARGETS[self.target].adapt(d) if self.target in TARGETS else None
        return {"surface": True, "kind": "verse", "delivery": d,
                "rendered": rendered, "memory_note": d.get("memory_note")}
