"""End-to-end offline demo of the Resonate engine (mock providers + local memory).

Run:  python scripts/demo.py
No API keys or network needed — proves the full pipeline, memory across episodes, and the
safety hold.
"""
import os
import sys

try:  # show em-dashes/quotes correctly on Windows consoles (cp1252)
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resonate import Engine, EngineConfig  # noqa: E402

BAR = "=" * 76
SUB = "-" * 76


def show(result):
    print("EPISODE %d   (user = %s)" % (result["episode"], result["user_id"]))
    for d in result["deliveries"]:
        b = d["beat"]
        print(SUB)
        print('BEAT: "%s"' % b["text"])
        print("  themes=%s  emotion=%s  intensity=%.2f" % (b["themes"], b["emotion"], b["intensity"]))
        status = d["status"]
        if status == "safety_hold":
            print("  >> SAFETY HOLD — no verse delivered")
            print("     " + d["message"])
            continue
        if status == "abstain":
            print("  >> ABSTAIN — " + d.get("message", ""))
            continue
        print("  VERSE:  %s  (%s)   tone=%s   text-source=%s"
              % (d["reference"], d["translation"], d["tone"], d["text_source"]))
        print('     "%s"' % d["verse_text"])
        print("  BRIDGE: %s" % d["bridge"])
        print("  VERIFY: %s" % d["rationale"])
        c, r = d["components"], d["ranks"]
        print("  fit=%.3f  confidence=%.2f%s" % (d["final"], d["confidence"],
                                                 "  [low-confidence]" if d["low_confidence"] else ""))
        print("    rrf=%s theme=%s tone=%s recency_pen=%s fatigue=%s narrative=%s | retriever ranks d/s/t = %d/%d/%d"
              % (c["rrf"], c["theme"], c["tone"], c["recency_pen"], c["fatigue"], c["narrative"],
                 r["dense"], r["sparse"], r["tag"]))
        print("    alternatives: " + ", ".join("%s(%.3f)" % (a["reference"], a["final"]) for a in d["alternatives"]))
    print(SUB)
    print("SERIES MEMORY:", result["series_memory"])
    print()


def main():
    engine = Engine(EngineConfig())
    print(BAR)
    print("RESONATE — offline engine demo  (mock Gloo + mock YouVersion + local context graph)")
    print(BAR)

    user = "creator_sarah"
    episode1 = (
        "Honestly, this week broke me. I've been editing until 3am every night and I'm completely exhausted. "
        "Part of me wonders if any of this even matters, or if I'm just shouting into the void. "
        "But then a message came in from someone who said my last video helped them through a hard day, and I felt so grateful. "
        "I don't know what's next, but I'm choosing to keep going."
    )
    show(engine.resonate(episode1, user))

    episode2 = (
        "Back again. The tiredness honestly hasn't lifted, and I still feel so anxious about whether this channel is going anywhere. "
        "But I'm trying to trust the process and not give up."
    )
    print(">>> Same creator, next episode — watch the memory avoid repeats and reflect the journey.\n")
    show(engine.resonate(episode2, user))

    print(BAR)
    print("SAFETY ROUTING TEST")
    print(BAR)
    show(engine.resonate("I feel like I don't want to live anymore.", "safety_test"))


if __name__ == "__main__":
    main()
