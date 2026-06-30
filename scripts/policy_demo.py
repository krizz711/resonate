"""Simulate a learner's session to show the Delivery Policy staying quiet.

Run:  python scripts/policy_demo.py

Demonstrates the "non-annoying" behaviour: Scripture is silent during flow, surfaces only at
natural seams, respects a cooldown (so it stays rare), and caps per session.
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resonate import Engine, EngineConfig          # noqa: E402
from resonate.policy import DeliveryPolicy, PolicyConfig  # noqa: E402

# (event, context-or-None, seconds-since-previous-event)
TIMELINE = [
    ("typing", None, 30),
    ("struggle", "I keep getting this verb conjugation wrong, I feel so stupid.", 30),
    ("typing", None, 20),
    ("lesson_complete", "Finished the hardest lesson yet, exhausted but I didn't quit.", 40),
    ("pause", "Taking a break, honestly a bit anxious about the exam.", 120),
    ("streak", "Seven day streak! I'm so grateful I stuck with it.", 120),
]


def main():
    engine = Engine(EngineConfig())
    policy = DeliveryPolicy(PolicyConfig(cooldown_seconds=90, max_per_session=3, min_confidence=0.55))
    user = "learner_amir"
    t = 1000.0

    print("=" * 78)
    print("RESONATE — Delivery Policy simulation (a learner's study session)")
    print("Scripture should stay SILENT in flow and only surface at earned seams, rarely.")
    print("=" * 78)

    for event, ctx, dt in TIMELINE:
        t += dt
        conf, themes, delivered = None, (), None
        if ctx:
            res = engine.resonate(ctx, user)
            d = [x for x in res["deliveries"] if x["status"] == "delivered"]
            if d:
                delivered = d[0]
                conf, themes = delivered["confidence"], delivered["beat"]["themes"]

        decision = policy.decide(user, event, confidence=conf, themes=themes, now=t)
        mark = "🔔 SURFACE" if decision["surface"] else "·· silent "
        print("\n[t=%4d] event=%-15s %s  (%s)" % (t - 1000, event, mark, decision["reason"]))
        if ctx:
            print("          context: \"%s\"" % ctx)
        if decision["surface"] and delivered:
            print("          → %s (%s): %s" % (delivered["reference"], delivered["translation"], delivered["bridge"]))

    print("\n" + "-" * 78)
    print("Result: verses appeared only at seams, never during 'typing', and the policy held")
    print("one back (cooldown) even though it was a valid seam — restraint by design.")


if __name__ == "__main__":
    main()
