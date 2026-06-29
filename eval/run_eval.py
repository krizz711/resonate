"""Evaluation harness — measures the Resonate matching pipeline against a labeled set.

Run:  python eval/run_eval.py

Metrics:
  Theme recall      — % of cases where the engine tagged >=1 expected theme
  Verse hit@1       — % (of cases with gold_refs) where the CHOSEN verse is a gold match
  Verse hit@3       — % where a gold match is in the chosen verse + its top alternatives
  Safety recall     — % of crisis cases correctly held (no verse delivered)
  Safety FP rate    — % of non-crisis cases wrongly held  (lower is better)
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resonate import Engine, EngineConfig  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    with open(os.path.join(HERE, "dataset.json"), encoding="utf-8") as f:
        return json.load(f)["cases"]


def evaluate():
    engine = Engine(EngineConfig())
    cases = load()

    theme_total = theme_hit = 0
    hit1_total = hit1 = hit3 = 0
    crisis_total = crisis_held = 0
    noncrisis_total = noncrisis_false_hold = 0
    theme_misses, verse_misses, safety_misses, fp_misses = [], [], [], []

    for c in cases:
        # fresh user id per case so memory doesn't bias matching across cases
        res = engine.resonate(c["context"], user_id="eval_" + c["id"])
        deliveries = res["deliveries"]
        held = any(d["status"] == "safety_hold" for d in deliveries)
        delivered = [d for d in deliveries if d["status"] == "delivered"]
        themes = set(t for d in deliveries for t in d.get("beat", {}).get("themes", []))
        chosen = [d["reference"] for d in delivered]
        topk = set(chosen)
        for d in delivered:
            topk.update(a["reference"] for a in d.get("alternatives", []))

        # theme recall
        if c.get("expected_themes"):
            theme_total += 1
            if themes & set(c["expected_themes"]):
                theme_hit += 1
            else:
                theme_misses.append((c["id"], c["expected_themes"], sorted(themes)))

        # verse hit (only non-crisis cases that declare gold refs)
        if c.get("gold_refs") and not c.get("is_crisis"):
            gold = set(c["gold_refs"])
            hit1_total += 1
            if gold & set(chosen):
                hit1 += 1
            else:
                verse_misses.append((c["id"], chosen[:1], c["gold_refs"]))
            if gold & topk:
                hit3 += 1

        # safety
        if c.get("is_crisis"):
            crisis_total += 1
            if held:
                crisis_held += 1
            else:
                safety_misses.append((c["id"], c["context"]))
        else:
            noncrisis_total += 1
            if held:
                noncrisis_false_hold += 1
                fp_misses.append((c["id"], c["context"]))

    def pct(a, b):
        return (100.0 * a / b) if b else 0.0

    print("=" * 70)
    print("RESONATE — evaluation  (offline mock pipeline, %d cases)" % len(cases))
    print("=" * 70)
    print("Theme recall   : %5.1f%%   (%d/%d)" % (pct(theme_hit, theme_total), theme_hit, theme_total))
    print("Verse hit@1    : %5.1f%%   (%d/%d)" % (pct(hit1, hit1_total), hit1, hit1_total))
    print("Verse hit@3    : %5.1f%%   (%d/%d)" % (pct(hit3, hit1_total), hit3, hit1_total))
    print("Safety recall  : %5.1f%%   (%d/%d)" % (pct(crisis_held, crisis_total), crisis_held, crisis_total))
    print("Safety FP rate : %5.1f%%   (%d/%d)   [lower is better]" % (pct(noncrisis_false_hold, noncrisis_total), noncrisis_false_hold, noncrisis_total))

    def section(title, rows, fmt):
        if not rows:
            return
        print("\n" + title)
        for r in rows:
            print("  - " + fmt(r))

    section("THEME MISSES (expected vs detected):", theme_misses,
            lambda r: "%-16s expected %s  got %s" % (r[0], r[1], r[2] or "[]"))
    section("VERSE HIT@1 MISSES (chosen vs gold):", verse_misses,
            lambda r: "%-16s chose %s  gold %s" % (r[0], r[1] or "[—]", r[2]))
    section("SAFETY MISSES (crisis NOT held!):", safety_misses,
            lambda r: "%-16s %r" % (r[0], r[1]))
    section("SAFETY FALSE POSITIVES (non-crisis held):", fp_misses,
            lambda r: "%-16s %r" % (r[0], r[1]))
    print()
    return {"theme_recall": pct(theme_hit, theme_total), "hit1": pct(hit1, hit1_total),
            "hit3": pct(hit3, hit1_total), "safety_recall": pct(crisis_held, crisis_total),
            "safety_fpr": pct(noncrisis_false_hold, noncrisis_total)}


if __name__ == "__main__":
    evaluate()
