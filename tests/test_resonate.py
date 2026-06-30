"""Unit tests for the Resonate engine internals (stdlib unittest — no deps).

Run:  python -m unittest discover -s tests        (from the repo root)
  or: python tests/test_resonate.py
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "eval"))

import run_eval                                                 # noqa: E402
from resonate import Engine, EngineConfig                      # noqa: E402
from resonate.models import Beat                                # noqa: E402
from resonate.memory import LocalMemory                         # noqa: E402
from resonate.retrieval import BM25, rrf_fuse, rank_indices, HybridRetriever  # noqa: E402
from resonate.verses import VerseStore                          # noqa: E402
from resonate.engine import _tone_fit                           # noqa: E402
from resonate.delivery import TARGETS, render                   # noqa: E402
from resonate.providers.gloo import MockGloo                    # noqa: E402
from resonate.policy import DeliveryPolicy, PolicyConfig         # noqa: E402


class TestRRF(unittest.TestCase):
    def test_fuse_rewards_top_ranks(self):
        # item 2 is ranked #1 by BOTH retrievers -> it must win.
        fused = rrf_fuse([[2, 0, 1], [2, 1, 0]], k=60)
        order = [i for i, _ in fused.most_common()]
        self.assertEqual(order[0], 2)
        # symmetric single-list appearances tie.
        only = rrf_fuse([[5], [3]], k=60)
        self.assertEqual(only[5], only[3])

    def test_rank_indices_desc(self):
        self.assertEqual(rank_indices([0.1, 0.9, 0.5]), [1, 2, 0])


class TestBM25(unittest.TestCase):
    def test_term_presence_scores_higher(self):
        bm = BM25([["peace", "rest", "calm"], ["anger", "rage"]])
        s = bm.scores(["peace"])
        self.assertGreater(s[0], 0.0)
        self.assertEqual(s[1], 0.0)


class TestToneFit(unittest.TestCase):
    def test_inside_range_is_one(self):
        v = {"intensity_fit": [0.4, 1.0]}
        self.assertEqual(_tone_fit(Beat(0, "", [], "", 0.5), v), 1.0)

    def test_falloff_outside_range(self):
        v = {"intensity_fit": [0.4, 1.0]}
        self.assertAlmostEqual(_tone_fit(Beat(0, "", [], "", 0.2), v), 0.6, places=3)
        self.assertAlmostEqual(_tone_fit(Beat(0, "", [], "", 0.0), v), 0.2, places=6)


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.m = LocalMemory(recency_window=8)
        self.m.start_episode("u")

    def test_recency_decays(self):
        self.m.add("u", ["anxiety"], 0.5, "Philippians 4:6-7")
        self.assertEqual(self.m.recency_penalty("u", "Philippians 4:6-7"), 1.0)
        self.assertEqual(self.m.recency_penalty("u", "Psalm 23:4"), 0.0)
        self.m.add("u", ["fear"], 0.5, "Psalm 23:4")
        self.assertAlmostEqual(self.m.recency_penalty("u", "Philippians 4:6-7"), 1.0 - 1 / 8, places=3)

    def test_theme_fatigue_and_narrative(self):
        for _ in range(3):
            self.m.add("u", ["weariness"], 0.6, "Galatians 6:9")
        self.assertGreater(self.m.theme_fatigue("u", ["weariness"]), 0.5)
        self.assertEqual(self.m.theme_fatigue("u", ["joy"]), 0.0)
        self.assertIn("weariness", self.m.narrative_themes("u"))
        self.assertEqual(self.m.narrative_continuity("u", ["weariness"]), 1.0)

    def test_patterns(self):
        self.m.add("u", ["hope"], 0.5, "Romans 8:28")
        p = self.m.patterns("u")
        self.assertEqual(p["total_events"], 1)
        self.assertEqual(p["episodes"], 1)


class TestSegmentationAndSafety(unittest.TestCase):
    def setUp(self):
        self.g = MockGloo(EngineConfig())

    def test_themes_detected(self):
        beats = self.g.segment("I'm so anxious about my exam tomorrow.")
        self.assertTrue(any("anxiety" in b.themes for b in beats))

    def test_dev_context_maps_to_perseverance(self):
        beats = self.g.segment("I'm stuck on 3 errors I can't fix.")
        self.assertTrue(any("perseverance" in b.themes for b in beats))

    def test_safety_detects_crisis(self):
        beats = self.g.segment("Honestly I don't want to live anymore.")
        self.assertTrue(any(self.g.safety(b) for b in beats))

    def test_safety_no_false_positive(self):
        for b in self.g.segment("I'm so grateful and full of joy today."):
            self.assertFalse(self.g.safety(b))


class TestDelivery(unittest.TestCase):
    def _delivery(self):
        return {"status": "delivered", "reference": "Philippians 4:6-7", "translation": "KJV",
                "verse_text": "Be careful for nothing...", "bridge": "A bridge line.",
                "tone": "comfort", "beat": {"themes": ["anxiety"]}}

    def test_targets_exist(self):
        for name in ("vscode", "discord", "wearable", "console"):
            self.assertIn(name, TARGETS)

    def test_vscode_adapt(self):
        out = TARGETS["vscode"].adapt(self._delivery())
        self.assertTrue(out["statusText"].startswith("✝"))
        self.assertIn("Philippians 4:6-7", out["reference"])
        self.assertIn("tooltipMarkdown", out)

    def test_render_only_delivered(self):
        result = {"deliveries": [self._delivery(), {"status": "safety_hold"}]}
        rendered = render(result, ["discord"])
        self.assertEqual(len(rendered["discord"]), 1)


class TestEngineEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eng = Engine(EngineConfig())

    def test_creator_episode_delivers_multiple(self):
        text = ("This week broke me. I've been editing until 3am and I'm completely exhausted. "
                "But someone said my video helped them and I felt so grateful.")
        res = self.eng.resonate(text, "t_creator")
        delivered = [d for d in res["deliveries"] if d["status"] == "delivered"]
        self.assertGreaterEqual(len(delivered), 2)
        for d in delivered:
            self.assertTrue(d["reference"])
            self.assertTrue(d["verse_text"])
            self.assertIn("bridge", d)

    def test_series_memory_note_after_recurrence(self):
        eng = Engine(EngineConfig())  # memory_persist defaults off -> deterministic
        u = "t_series"
        note = None
        for _ in range(4):
            res = eng.resonate("I'm so anxious I can't stop worrying about everything.", u)
            d = [x for x in res["deliveries"] if x["status"] == "delivered"]
            if d:
                note = d[0].get("memory_note")
        self.assertTrue(note and "anxiety" in note)

    def test_theme_count(self):
        from resonate.memory import LocalMemory
        m = LocalMemory()
        m.add("u", ["anxiety"], 0.5, "X")
        m.add("u", ["anxiety", "fear"], 0.5, "Y")
        self.assertEqual(m.theme_count("u", "anxiety"), 2)
        self.assertEqual(m.theme_count("u", "joy"), 0)

    def test_safety_hold_path(self):
        res = self.eng.resonate("I don't want to live anymore.", "t_safety")
        self.assertTrue(any(d["status"] == "safety_hold" for d in res["deliveries"]))

    def test_memory_grows_and_no_immediate_repeat(self):
        u = "t_mem"
        line = "I'm completely exhausted and burned out."
        first = self.eng.resonate(line, u)
        second = self.eng.resonate(line, u)
        self.assertGreater(second["series_memory"]["total_events"],
                           first["series_memory"]["total_events"])
        r1 = [d["reference"] for d in first["deliveries"] if d["status"] == "delivered"]
        r2 = [d["reference"] for d in second["deliveries"] if d["status"] == "delivered"]
        if r1 and r2:  # same input twice should not yield the identical verse back-to-back
            self.assertNotEqual(r1[0], r2[0])


class TestDeliveryPolicy(unittest.TestCase):
    def test_suppresses_mid_flow(self):
        p = DeliveryPolicy(PolicyConfig())
        self.assertFalse(p.decide("u", "typing", confidence=0.9, now=0.0)["surface"])

    def test_surfaces_at_seam(self):
        p = DeliveryPolicy(PolicyConfig())
        self.assertTrue(p.decide("u", "struggle", confidence=0.9, now=0.0)["surface"])

    def test_cooldown_blocks_rapid_repeat(self):
        p = DeliveryPolicy(PolicyConfig(cooldown_seconds=90, max_per_session=9, min_confidence=0))
        self.assertTrue(p.decide("u", "struggle", confidence=0.9, now=0.0)["surface"])
        self.assertFalse(p.decide("u", "streak", confidence=0.9, now=10.0)["surface"])
        self.assertTrue(p.decide("u", "streak", confidence=0.9, now=100.0)["surface"])

    def test_session_cap(self):
        p = DeliveryPolicy(PolicyConfig(cooldown_seconds=0, max_per_session=2, min_confidence=0))
        self.assertTrue(p.decide("u", "struggle", confidence=0.9, now=0)["surface"])
        self.assertTrue(p.decide("u", "struggle", confidence=0.9, now=1)["surface"])
        self.assertFalse(p.decide("u", "struggle", confidence=0.9, now=2)["surface"])

    def test_low_confidence_silent(self):
        p = DeliveryPolicy(PolicyConfig())
        self.assertFalse(p.decide("u", "struggle", confidence=0.2, now=0)["surface"])

    def test_manual_always(self):
        p = DeliveryPolicy(PolicyConfig())
        self.assertTrue(p.decide("u", "typing", manual=True, now=0)["surface"])

    def test_dismiss_backoff(self):
        p = DeliveryPolicy(PolicyConfig(cooldown_seconds=0, min_confidence=0, dismiss_backoff=5))
        self.assertTrue(p.decide("u", "struggle", confidence=0.9, themes=["anxiety"], now=0)["surface"])
        p.record_dismiss("u", ["anxiety"])
        self.assertFalse(p.decide("u", "struggle", confidence=0.9, themes=["anxiety"], now=1)["surface"])


class TestResponder(unittest.TestCase):
    def setUp(self):
        from resonate.responder import Responder
        self.r = Responder(target="discord")

    def test_verse_path(self):
        out = self.r.respond("ru1", "I feel like I'm failing everyone and I can't keep up.")
        self.assertTrue(out["surface"] and out["kind"] == "verse")
        self.assertIn("content", out["rendered"])

    def test_silent_on_neutral(self):
        out = self.r.respond("ru2", "what's the capital of France?")
        self.assertFalse(out["surface"])

    def test_help_on_crisis(self):
        out = self.r.respond("ru3", "honestly I do not want to live anymore")
        self.assertTrue(out["surface"] and out["kind"] == "help")


class TestEvalThresholds(unittest.TestCase):
    """Turns the evaluation harness into a regression guard — quality can't silently drop."""

    def test_quality_thresholds(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            m = run_eval.evaluate()
        self.assertEqual(m["safety_recall"], 100.0, "a crisis case was not held")
        self.assertEqual(m["safety_fpr"], 0.0, "a non-crisis case was wrongly held")
        self.assertEqual(m["theme_recall"], 100.0)
        self.assertGreaterEqual(m["hit3"], 95.0)
        self.assertGreaterEqual(m["hit1"], 80.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
