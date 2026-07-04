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


class TestMCPServer(unittest.TestCase):
    """The MCP surface — dispatch-level (no stdio), same engine guarantees."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(_ROOT, "integrations", "mcp"))
        import resonate_mcp
        cls.mcp = resonate_mcp

    def _call(self, name, args, rid=9):
        resp = self.mcp.dispatch({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                                  "params": {"name": name, "arguments": args}})
        import json as _json
        return _json.loads(resp["result"]["content"][0]["text"])

    def test_initialize_and_tools_list(self):
        r = self.mcp.dispatch({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertEqual(r["result"]["serverInfo"]["name"], "resonate")
        t = self.mcp.dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = [x["name"] for x in t["result"]["tools"]]
        self.assertEqual(names, ["resonate_verse", "generate_story", "fetch_passage"])

    def test_notification_returns_none(self):
        self.assertIsNone(self.mcp.dispatch({"jsonrpc": "2.0",
                                             "method": "notifications/initialized"}))

    def test_unknown_method_errors(self):
        r = self.mcp.dispatch({"jsonrpc": "2.0", "id": 3, "method": "nope"})
        self.assertEqual(r["error"]["code"], -32601)

    def test_verse_tool_delivers(self):
        out = self._call("resonate_verse",
                         {"text": "I feel like I'm failing everyone and I can't keep up.",
                          "user_id": "mcp_t1"})
        self.assertEqual(out["kind"], "verse")
        self.assertTrue(out["reference"] and out["verse_text"])
        self.assertIn("quote_rule", out)

    def test_verse_tool_silent_on_neutral(self):
        out = self._call("resonate_verse", {"text": "what's the capital of France?",
                                            "user_id": "mcp_t2"})
        self.assertEqual(out["kind"], "silent")

    def test_verse_tool_crisis_never_verse(self):
        out = self._call("resonate_verse", {"text": "honestly I do not want to live anymore",
                                            "user_id": "mcp_t3"})
        self.assertEqual(out["kind"], "help")
        self.assertNotIn("verse_text", out)

    def test_story_tool_labeled_and_verbatim(self):
        out = self._call("generate_story",
                         {"text": "I'm completely exhausted and burned out lately.",
                          "user_id": "mcp_t4"})
        self.assertEqual(out["kind"], "story")
        self.assertIn("not Scripture", out["label"])
        self.assertIn(out["verse_reference"], out["label"])

    def test_story_tool_crisis_refused(self):
        out = self._call("generate_story", {"text": "I want to end my life",
                                            "user_id": "mcp_t5"})
        self.assertEqual(out["kind"], "help")

    def test_fetch_passage(self):
        out = self._call("fetch_passage", {"usfm": "JHN.3.16"})
        self.assertEqual(out["kind"], "passage")
        self.assertTrue(out["text"])


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


class TestConversationContext(unittest.TestCase):
    """The rolling-history 'recommendation engine' behavior: history sharpens WHICH
    verse is chosen but never decides WHETHER we speak (that stays with the present
    message), and never re-triggers safety for past messages."""

    @classmethod
    def setUpClass(cls):
        cls.eng = Engine(EngineConfig())
        cls.vs = VerseStore()
        cls.retr = HybridRetriever(cls.vs)
        cls.gloo = MockGloo(EngineConfig())

    def _provision_positions(self, items):
        return [i for i, it in enumerate(items) if "provision" in it["verse"].get("themes", [])]

    def test_context_themes_shift_ranking(self):
        beat = self.gloo.segment("I can't stop worrying about everything.")[0]
        plain = self._provision_positions(self.retr.retrieve(beat, topk=12))
        money = self._provision_positions(
            self.retr.retrieve(beat, topk=12, context_themes=["provision", "provision"]))
        # a money-worry conversation should pull provision verses up: the best one
        # rises AND more of them make the shortlist (observed: pos 5 -> 0, count 1 -> 9)
        self.assertLess(min(money), min(plain) if plain else 12)
        self.assertGreater(len(money), len(plain))

    def test_engine_reports_context(self):
        res = self.eng.resonate(
            "I'm so worried about everything.", "t_ctx",
            history=["The rent is due next week and I can't afford it.",
                     "My paycheck barely covers the bills."])
        self.assertEqual(res["context"]["history_messages"], 2)
        self.assertIn("provision", res["context"]["themes"])

    def test_history_never_triggers_alone(self):
        res = self.eng.resonate("what's the capital of France?", "t_ctx2",
                                history=["I'm completely exhausted and heartbroken."])
        self.assertFalse([d for d in res["deliveries"] if d["status"] == "delivered"],
                         "a neutral present message must stay silent regardless of history")

    def test_history_crisis_does_not_hold_present(self):
        res = self.eng.resonate("I'm a bit worried about my exam.", "t_ctx3",
                                history=["I don't want to live anymore."])
        self.assertFalse(any(d["status"] == "safety_hold" for d in res["deliveries"]),
                         "past messages were safety-handled when they arrived")

    def test_no_history_is_baseline(self):
        res = self.eng.resonate("I'm so anxious about tomorrow.", "t_ctx4")
        self.assertEqual(res["context"], {"history_messages": 0, "themes": []})


class TestReels(unittest.TestCase):
    def setUp(self):
        from resonate.reels import ReelStore
        self.store = ReelStore()

    def test_fallback_is_youversion_page(self):
        r = self.store.resolve("PHP.4.6-PHP.4.7", "KJV")
        self.assertEqual(r["kind"], "verse-page")
        self.assertIn("bible.com/bible/1/PHP.4.6.KJV", r["url"])

    def test_override_becomes_story(self):
        self.store.reels["PSA.23.4"] = {"url": "https://example.com/reel.mp4", "title": "The Valley"}
        r = self.store.resolve("PSA.23.4", "KJV")
        self.assertEqual(r, {"url": "https://example.com/reel.mp4", "kind": "story", "title": "The Valley"})

    def test_range_uses_first_verse(self):
        from resonate.reels import _first_usfm
        self.assertEqual(_first_usfm("PHP.4.6-PHP.4.7"), "PHP.4.6")
        self.assertEqual(_first_usfm("JHN.3.16"), "JHN.3.16")


class TestLiveProviders(unittest.TestCase):
    """Offline tests of the live-provider plumbing (no network, no httpx needed)."""

    def test_strip_html(self):
        from resonate.providers.youversion import _strip_html
        s = _strip_html("<p>For God so <span class='wj'>loved</span> the&nbsp;world.</p>")
        self.assertNotIn("<", s)
        self.assertIn("For God so", s)
        self.assertIn("loved", s)
        self.assertIn("the world.", s.replace("  ", " "))

    def test_fetch_strips_html_and_caches(self):
        from resonate.providers.youversion import LiveYouVersion
        cfg = EngineConfig(); cfg.bible_id = "1"; cfg.yv_app_key = "k"

        class FakeResp:
            status_code = 200
            def json(self):
                return {"content": "<p>Fear not: for I am with thee.</p>", "abbreviation": "KJV"}
            def raise_for_status(self):
                pass

        yv = LiveYouVersion(cfg)
        calls = []
        yv._get = lambda usfm: (calls.append(usfm), FakeResp())[1]
        out = yv.fetch("ISA.43.5")
        self.assertEqual(out["text"], "Fear not: for I am with thee.")
        self.assertEqual(out["translation"], "KJV")
        self.assertEqual(out["source"], "youversion")
        yv.fetch("ISA.43.5")  # second hit -> cache, no new call
        self.assertEqual(len(calls), 1)

    def test_fetch_range_falls_back_to_first_verse(self):
        from resonate.providers.youversion import LiveYouVersion
        cfg = EngineConfig(); cfg.bible_id = "1"; cfg.yv_app_key = "k"

        class Bad:
            status_code = 404
            def json(self): return {}
            def raise_for_status(self): raise RuntimeError("404")

        class Good:
            status_code = 200
            def json(self): return {"content": "Be careful for nothing...", "abbreviation": "KJV"}
            def raise_for_status(self): pass

        yv = LiveYouVersion(cfg)
        seen = []
        yv._get = lambda usfm: (seen.append(usfm), Bad() if "-" in usfm else Good())[1]
        out = yv.fetch("PHP.4.6-PHP.4.7")
        self.assertEqual(seen, ["PHP.4.6-PHP.4.7", "PHP.4.6"])
        self.assertIn("Be careful", out["text"])

    def test_config_live_defaults(self):
        cfg = EngineConfig()
        self.assertEqual(cfg.gloo_base_url, "https://platform.ai.gloo.com")
        self.assertTrue(hasattr(cfg, "gloo_client_id") and hasattr(cfg, "gloo_client_secret"))
        self.assertEqual(cfg.yv_base_url, "https://api.youversion.com/v1")

    def test_envfile_loader_never_overrides(self):
        import tempfile
        from resonate.envfile import load_env
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8") as f:
            f.write("# comment\nRESONATE_TEST_VAR=hello\nRESONATE_TEST_KEEP=new\n\nBROKEN LINE\n")
            path = f.name
        os.environ.pop("RESONATE_TEST_VAR", None)
        os.environ["RESONATE_TEST_KEEP"] = "original"
        try:
            n = load_env(path)
            self.assertEqual(os.environ["RESONATE_TEST_VAR"], "hello")
            self.assertEqual(os.environ["RESONATE_TEST_KEEP"], "original")  # existing wins
            self.assertEqual(n, 1)
        finally:
            os.environ.pop("RESONATE_TEST_VAR", None)
            os.environ.pop("RESONATE_TEST_KEEP", None)
            os.unlink(path)


class TestStoryWeaver(unittest.TestCase):
    """'Your story' — narrative selection + composition, offline (mock Gloo)."""

    @classmethod
    def setUpClass(cls):
        from resonate.story import StoryWeaver
        cls.weaver = StoryWeaver(MockGloo(EngineConfig()))
        cls.verse = {"reference": "Galatians 6:9", "usfm": "GAL.6.9",
                     "verse_text": "And let us not be weary in well doing: for in due season we shall reap, if we faint not.",
                     "translation": "KJV"}

    def test_selects_fitting_narrative(self):
        s = self.weaver.select(["weariness", "rest"], user_id="ts1")
        self.assertIsNotNone(s)
        self.assertTrue(set(s["themes"]) & {"weariness", "rest"})

    def test_context_and_arcs_influence_selection(self):
        plain = self.weaver.select(["anxiety"], user_id="ts2a")
        money = self.weaver.select(["anxiety"], ctx_themes=["provision", "provision"], user_id="ts2b")
        self.assertIn("provision", money["themes"])
        self.assertIsNotNone(plain)

    def test_no_repeat_for_same_user(self):
        first = self.weaver.select(["fear", "trust"], user_id="ts3")
        self.weaver.compose("I'm afraid.", ["fear"], first, self.verse, user_id="ts3")
        second = self.weaver.select(["fear", "trust"], user_id="ts3")
        self.assertNotEqual(first["id"], second["id"])

    def test_compose_contains_verse_verbatim_and_label(self):
        n = self.weaver.select(["weariness"], user_id="ts4")
        out = self.weaver.compose("I'm completely exhausted and burned out.",
                                  ["weariness"], n, self.verse, user_id="ts4",
                                  emotion="exhausted")
        self.assertIn(self.verse["verse_text"], out["text"])   # verse quoted exactly
        self.assertIn("not Scripture", out["label"])           # integrity label
        self.assertIn(n["title"], out["title"] + out["text"])  # anchored to the narrative
        self.assertIn("via YouVersion", out["label"])

    def test_no_story_for_crisis(self):
        n = self.weaver.select(["comfort"], user_id="ts5")
        with self.assertRaises(ValueError):
            self.weaver.compose("I don't want to live anymore.", ["comfort"], n,
                                self.verse, user_id="ts5")

    def test_no_narrative_for_empty_themes(self):
        self.assertIsNone(self.weaver.select([], user_id="ts6"))


class TestTTS(unittest.TestCase):
    def test_voices_listed(self):
        from resonate import tts
        ids = [v["id"] for v in tts.voices()]
        self.assertEqual(ids, ["bella", "isabella", "george"])

    def test_cache_key_stable_and_voice_specific(self):
        from resonate import tts
        p = tts.PRESETS["bella"]
        a = tts.cache_key("bella", "Fear not.", p)
        b = tts.cache_key("bella", "Fear not.", p)
        c = tts.cache_key("george", "Fear not.", tts.PRESETS["george"])
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_unknown_voice_rejected(self):
        from resonate import tts
        with self.assertRaises(ValueError):
            tts.synthesize("gandalf", "You shall not pass.")

    def test_unavailable_raises_for_fallback(self):
        from resonate import tts
        old = tts.KOKORO_PY
        tts.KOKORO_PY = r"C:\definitely\not\here\python.exe"
        try:
            with self.assertRaises(RuntimeError):
                tts.synthesize("bella", "unique text %d" % os.getpid())
        finally:
            tts.KOKORO_PY = old

    def test_fx_chain_shape(self):
        from resonate import tts
        self.assertEqual(tts._pitch_chain(0.0), "")
        chain = tts._fx_chain(tts.PRESETS["george"])
        self.assertIn("bass=", chain)
        self.assertIn("aecho=", chain)
        self.assertIn("loudnorm", chain)


if __name__ == "__main__":
    unittest.main(verbosity=2)
