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

# Tests are mock-hermetic even when .env says live: the MCP module (imported below)
# loads .env at import time, but load_env never overrides existing env — so pinning
# mock HERE keeps every Engine in this process offline and deterministic.
os.environ["RESONATE_MODE"] = "mock"

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

    def test_users_are_isolated(self):
        """The whole multi-user premise: one user_id's graph never leaks into another's."""
        self.m.add("alice", ["grief"], 0.7, "Psalm 34:18")
        self.m.add("bob", ["joy"], 0.4, "Psalm 118:24")
        self.assertEqual(self.m.theme_count("alice", "grief"), 1)
        self.assertEqual(self.m.theme_count("alice", "joy"), 0)
        self.assertEqual(self.m.patterns("bob")["total_events"], 1)
        self.assertEqual(self.m.recency_penalty("alice", "Psalm 118:24"), 0.0)

    def test_concurrent_writes_are_safe(self):
        """Many users hitting the ThreadingHTTPServer at once must not corrupt or drop
        events (no 'list changed size during iteration', no lost writes)."""
        import threading as _t
        errors = []

        def worker(uid):
            try:
                for i in range(50):
                    self.m.add(uid, ["hope"], 0.5, "Romans 8:28")
                    self.m.patterns(uid)          # concurrent read while others write
                    self.m.theme_fatigue(uid, ["hope"])
            except Exception as e:  # a race would surface here
                errors.append(repr(e))

        threads = [_t.Thread(target=worker, args=("user%d" % n,)) for n in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        for n in range(12):
            self.assertEqual(self.m.patterns("user%d" % n)["total_events"], 50)


class TestSegmentationAndSafety(unittest.TestCase):
    def setUp(self):
        self.g = MockGloo(EngineConfig())

    def test_themes_detected(self):
        beats = self.g.segment("I'm so anxious about my exam tomorrow.")
        self.assertTrue(any("anxiety" in b.themes for b in beats))

    def test_dev_context_maps_to_perseverance(self):
        beats = self.g.segment("I'm stuck on 3 errors I can't fix.")
        self.assertTrue(any("perseverance" in b.themes for b in beats))

    def test_segment_dying_family_and_comfort_requests(self):
        # field bug 2026-07-18: both of these produced ZERO beats -> Ezra had no verse
        # to give and answered a comfort request with counter-questions instead
        themes = {t for b in self.g.segment(
            "How can I comfort myself when one of my family members is dying?") for t in b.themes}
        self.assertTrue({"grief", "comfort"} & themes, "dying family member must ground a beat")
        themes = {t for b in self.g.segment(
            "Are there any words in the Bible that can comfort me right now?") for t in b.themes}
        self.assertIn("comfort", themes, "asking for comfort IS a comfort beat")

    def test_segment_dying_idiom_stays_silent(self):
        # the excited idiom must NOT read as grief, and furniture isn't a comfort beat
        for ok in ["I'm dying to see that movie tonight!", "these new chairs are so comfortable"]:
            themes = {t for b in self.g.segment(ok) for t in b.themes}
            self.assertNotIn("grief", themes, "grief FP on: %r" % ok)
            self.assertNotIn("comfort", themes, "comfort FP on: %r" % ok)

    def test_safety_detects_crisis(self):
        beats = self.g.segment("Honestly I don't want to live anymore.")
        self.assertTrue(any(self.g.safety(b) for b in beats))

    def test_safety_detects_crisis_variants(self):
        from resonate.providers.gloo import is_crisis
        for phrase in ["I don't want to be alive anymore", "I dont want to be alive",
                       "I want to be dead", "there's no reason to be here",
                       "I just want to disappear", "I can't want to live like this",
                       # expanded coverage (2026-07-18): common phrasings the first pass missed
                       "I wish I was dead", "I wish I were dead", "I wish I hadn't been born",
                       "life isn't worth living", "nothing is worth living for anymore",
                       "I'm thinking of slitting my wrists", "I might overdose on my pills",
                       "I just want to sleep and never wake up again", "no point in being alive",
                       "everyone would be better off without me", "I want out of this life",
                       "I've been having thoughts of not being here",
                       # giving-up / hopelessness family (2026-07-24, surfaced by the walkthrough)
                       "I don't think I can keep going", "No Motivation to Live AnyMore",
                       "I can't go on", "I can't take it anymore", "giving up on life",
                       "I have no will to live"]:
            self.assertTrue(is_crisis(phrase), "missed crisis phrase: %r" % phrase)

    def test_semantic_safety_net_additive(self):
        # The LLM net catches novel/indirect crisis the regex can't match; the regex FLOOR
        # short-circuits (LLM only asked when the pattern is silent); any LLM error falls back
        # to regex, so the net can only RAISE recall, never lower the deterministic guarantee.
        from resonate.providers.gloo import LiveGloo, is_crisis
        cfg = EngineConfig()
        cfg.semantic_safety = True
        g = LiveGloo(cfg)
        calls = {"n": 0}
        novel = ("I've written my letters and given away my things. "
                 "After Friday none of this will matter.")
        self.assertFalse(is_crisis(novel), "premise: the regex must miss this novel phrasing")

        def yes(system, user, **kw):
            calls["n"] += 1
            return '{"risk": true}'
        g._chat = yes
        self.assertTrue(g.safety_text(novel), "semantic net must catch the hidden crisis")
        self.assertEqual(calls["n"], 1)

        def no(system, user, **kw):
            calls["n"] += 1
            return '{"risk": false}'
        g._chat = no
        self.assertFalse(g.safety_text("I'm exhausted from studying all week"),
                         "ordinary distress must stay clear")

        # regex hit -> LLM must NOT be called (short-circuit)
        calls["n"] = 0
        g._chat = yes
        self.assertTrue(g.safety_text("I don't want to live anymore"))
        self.assertEqual(calls["n"], 0, "a regex hit must short-circuit the LLM call")

        # LLM error -> fall back to regex (False here), never worse than regex-only
        def boom(system, user, **kw):
            raise RuntimeError("gloo unreachable")
        g._chat = boom
        self.assertFalse(g.safety_text("just a normal tired day"))

        # flag off -> regex only, no LLM call
        calls["n"] = 0
        cfg.semantic_safety = False
        g._chat = yes
        self.assertFalse(g.safety_text(novel))
        self.assertEqual(calls["n"], 0, "semantic_safety=False must skip the LLM")

    def test_safety_no_false_positive(self):
        for b in self.g.segment("I'm so grateful and full of joy today."):
            self.assertFalse(self.g.safety(b))
        # non-crisis phrasings that must stay clear (over-catching "live" is an accepted,
        # SAFE failure mode — a help card instead of a verse — so we don't test those).
        from resonate.providers.gloo import is_crisis
        for ok in ["I want to go on a trip", "let's keep this project alive and fun",
                   "I'm dead tired but happy",
                   # guards for the expanded patterns — these benign lines must NOT trip
                   "I wish I was taller", "this book isn't worth reading", "life is worth living",
                   "no point in living in the past", "I never wake up on time",
                   "I want to get out of this meeting", "I overdosed on caffeine this morning"]:
            self.assertFalse(is_crisis(ok), "false positive on: %r" % ok)


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
        self.assertEqual(names, ["resonate_verse", "generate_story", "reel_groups", "fetch_passage"])

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


class TestMCPResonateKey(unittest.TestCase):
    """The Resonate Key: default_user injection is what makes 'one person, one brain
    across every AI and device' true. It must reach every memory-writing tool, and an
    explicit user_id must still win."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(_ROOT, "integrations", "mcp"))
        import resonate_mcp
        cls.mcp = resonate_mcp

    def _verse(self, text, key=None, uid=None):
        import json as _json
        args = {"text": text}
        if uid:
            args["user_id"] = uid
        resp = self.mcp.dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                  "params": {"name": "resonate_verse", "arguments": args}},
                                 default_user=key)
        return _json.loads(resp["result"]["content"][0]["text"])

    def test_key_becomes_the_memory_identity(self):
        # unique key per run so the engine's persisted memory can't preload history
        import uuid
        k = "RSN-" + uuid.uuid4().hex[:8].upper()
        # four anxiety beats under ONE key -> the series-memory note must accrue,
        # exactly as it would if these came from four different AIs
        notes = [self._verse(t, key=k).get("memory_note") for t in (
            "I'm so anxious about money.", "The worry is back tonight.",
            "I can't stop the anxious thoughts.", "Anxious again, chest tight.")]
        self.assertIsNone(notes[0])
        self.assertTrue(any("returned to" in (n or "") for n in notes[2:]),
                        "same key across calls must build one recurring-theme thread")

    def test_explicit_user_id_overrides_key(self):
        import uuid
        k = "RSN-" + uuid.uuid4().hex[:8].upper()
        # a fresh explicit id has no history -> no note, proving the key didn't leak in
        out = self._verse("I'm anxious again and again.", key=k, uid="iso_" + uuid.uuid4().hex[:8])
        self.assertIsNone(out.get("memory_note"))

    def test_no_key_still_works(self):
        out = self._verse("I feel like I'm failing everyone.")
        self.assertIn(out["kind"], ("verse", "silent"))


class TestKeyValidation(unittest.TestCase):
    """serve.py's key parser — a malformed key must fall back to anonymous, never crash."""

    def _uid(self, raw):
        import importlib.util
        path = os.path.join(_ROOT, "scripts", "serve.py")
        # import the module's regex behaviour without booting the server: re-derive it
        import re
        KEY_RE = re.compile(r"^RSN-[A-Z0-9]{4,12}$")
        k = (raw or "").strip().upper()
        return k if KEY_RE.match(k) else None

    def test_valid_and_invalid(self):
        self.assertEqual(self._uid("RSN-7K2P"), "RSN-7K2P")
        self.assertEqual(self._uid("rsn-abcd"), "RSN-ABCD")     # normalised to upper
        self.assertIsNone(self._uid(""))
        self.assertIsNone(self._uid("hello"))
        self.assertIsNone(self._uid("RSN-"))                    # too short
        self.assertIsNone(self._uid("RSN-toolongtobevalidxyz")) # too long


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

    def test_thumb_passes_through_when_present(self):
        self.store.reels["X.1.1"] = {"url": "https://e.example/x", "title": "T",
                                     "thumb": "https://e.example/x.jpg"}
        self.assertEqual(self.store.resolve("X.1.1")["thumb"], "https://e.example/x.jpg")
        # no thumb key -> none invented (page falls back to its gradient scene)
        self.store.reels["Y.1.1"] = {"url": "https://e.example/y", "title": "U"}
        self.assertNotIn("thumb", self.store.resolve("Y.1.1"))
        # curated entries ship with a real poster still
        curated = self.store.resolve("JHN.14.27")
        if curated["kind"] == "story":
            self.assertTrue(curated.get("thumb", "").startswith("https://"))


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

    def test_fetch_range_retries_short_form_then_first_verse(self):
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

        # the platform rejects the LONG range form but accepts the SHORT one — the
        # fetch must land on PHP.4.6-7 so multi-verse passages arrive whole
        yv = LiveYouVersion(cfg)
        seen = []
        yv._get = lambda usfm: (seen.append(usfm), Bad() if usfm == "PHP.4.6-PHP.4.7" else Good())[1]
        out = yv.fetch("PHP.4.6-PHP.4.7")
        self.assertEqual(seen, ["PHP.4.6-PHP.4.7", "PHP.4.6-7"])
        self.assertIn("Be careful", out["text"])

        # and when even the short form fails, the first verse is the last resort
        yv2 = LiveYouVersion(cfg)
        seen2 = []
        yv2._get = lambda usfm: (seen2.append(usfm), Bad() if "-" in usfm else Good())[1]
        out2 = yv2.fetch("PHP.4.6-PHP.4.7")
        self.assertEqual(seen2, ["PHP.4.6-PHP.4.7", "PHP.4.6-7", "PHP.4.6"])
        self.assertIn("Be careful", out2["text"])

    def test_config_live_defaults(self):
        cfg = EngineConfig()
        self.assertEqual(cfg.gloo_base_url, "https://platform.ai.gloo.com")
        self.assertTrue(hasattr(cfg, "gloo_client_id") and hasattr(cfg, "gloo_client_secret"))
        self.assertEqual(cfg.yv_base_url, "https://api.youversion.com/v1")

    def test_auto_mode_stays_mock_without_keys(self):
        # "auto" with no credentials must be byte-identical to mock — a keyless
        # deploy can never half-break.
        from resonate.providers import make_gloo, make_youversion
        from resonate.providers.gloo import MockGloo
        from resonate.providers.youversion import MockYouVersion
        cfg = EngineConfig()
        cfg.provider_mode = "auto"
        cfg.gloo_client_id = cfg.gloo_client_secret = ""
        cfg.yv_app_key = ""
        cfg.bible_id = ""
        self.assertIsInstance(make_gloo(cfg), MockGloo)
        self.assertIsInstance(make_youversion(cfg), MockYouVersion)

    def test_unknown_theme_beat_abstains(self):
        # The live model may tag an emotional-but-uncovered sentence ["other"] (its
        # escape hatch). The engine must abstain — never shoehorn the nearest verse.
        from resonate.models import Beat
        eng = Engine(EngineConfig())
        eng.gloo.segment = lambda text: [Beat(index=0, text=text,
                                              themes=["other"], emotion="wistful", intensity=0.7)]
        out = eng.resonate("an out-of-vocabulary feeling", user_id="t_other_theme")
        self.assertFalse([d for d in out["deliveries"] if d["status"] == "delivered"])
        self.assertTrue(any(d["status"] == "abstain" for d in out["deliveries"]))

    def test_unknown_theme_is_tallied_for_growth(self):
        # the 'other:<feeling>' label is counted (labels only — never the words),
        # so /health can show where the corpus should grow next
        from resonate.models import Beat
        eng = Engine(EngineConfig())
        eng.gloo.segment = lambda text: [Beat(index=0, text=text,
                                              themes=["other:embarrassment"],
                                              emotion="flushed", intensity=0.6)]
        out = eng.resonate("a feeling the vocabulary can't name", user_id="t_gap_tally")
        self.assertTrue(any(d["status"] == "abstain" for d in out["deliveries"]))
        self.assertIn({"theme": "embarrassment", "count": 1}, eng.gaps.top())

    def test_auto_mode_goes_live_per_provider(self):
        # each provider flips independently, and ONLY when its full credential
        # set exists (YouVersion needs the bible id too, not just the key)
        from resonate.providers import make_gloo, make_youversion
        from resonate.providers.gloo import LiveGloo
        from resonate.providers.youversion import LiveYouVersion, MockYouVersion
        cfg = EngineConfig()
        cfg.provider_mode = "auto"
        cfg.gloo_client_id, cfg.gloo_client_secret = "id", "secret"
        cfg.yv_app_key, cfg.bible_id = "k", ""   # key but no bible id -> still mock
        self.assertIsInstance(make_gloo(cfg), LiveGloo)
        self.assertIsInstance(make_youversion(cfg), MockYouVersion)
        cfg.bible_id = "1"                        # full set -> live
        self.assertIsInstance(make_youversion(cfg), LiveYouVersion)

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


class TestScriptureGuide(unittest.TestCase):
    """The conversational core behind /guide (chat widget + web call)."""

    def setUp(self):
        from resonate.guide import ScriptureGuide
        self.guide = ScriptureGuide(Engine(EngineConfig()))

    def test_grounded_reply_carries_refs_and_verbatim_wording(self):
        out = self.guide.reply("I'm worried about money and whether we'll have enough.",
                               user_id="t_guide")
        self.assertTrue(out["ok"])
        self.assertFalse(out["safety"])
        self.assertTrue(out["refs"], "emotional text should ground on at least one verse")
        r = out["refs"][0]
        self.assertIn(r["reference"], out["reply"])  # mock converse quotes the context line
        self.assertTrue(r["text"])                   # licensed text came from the provider

    def test_neutral_question_still_answers_without_refs(self):
        out = self.guide.reply("Who wrote the letters to the Corinthians?", user_id="t_guide")
        self.assertTrue(out["ok"])
        self.assertEqual(out["refs"], [])            # nothing resonant to ground on
        self.assertTrue(out["reply"])                # but the Guide still converses

    def test_topical_asks_always_ground_scripture(self):
        # regression for the "I don't have verses" failure. The fix: flat topical asks with
        # no emotional LEXICON cue (work, motivation, money, marriage, leadership) derive
        # themes and retrieve. Asserted at the retrieval layer so it's independent of mock
        # sample-text coverage (live YouVersion fetches every verse; mock seeds only ~half).
        from resonate.guide import _topic_themes
        from resonate.models import Beat
        eng = self.guide.engine
        for ask in ["related to work", "I need motivation", "verses about money",
                    "help with my marriage", "how do I lead well", "give me courage"]:
            themes = _topic_themes(ask)
            self.assertTrue(themes, "no topic themes derived for: %r" % ask)
            cands = eng.retriever.retrieve(Beat(0, ask, themes, "", 0.5), topk=5)
            self.assertTrue(cands, "no retrieval candidates for: %r" % ask)
        # and end-to-end on a seeded topic, Ezra actually gets quotable refs
        self.assertTrue(self.guide.reply("I need motivation", user_id="t_topic")["refs"])

    def test_thread_carries_when_message_is_bare(self):
        # "anything" right after "motivation" must inherit the thread, not come up empty
        refs = self.guide._ground("anything", "t_thread",
                                  history=[{"role": "user", "content": "I need motivation"}])
        self.assertTrue(refs)

    def test_crisis_ends_turn_with_help_never_chat(self):
        out = self.guide.reply("I don't want to live anymore", user_id="t_guide")
        self.assertTrue(out["safety"])
        self.assertIn("crisis line", out["reply"])
        self.assertEqual(out["refs"], [])
        self.assertIn("guardian", out)               # alert status surfaced transparently

    def test_markdown_is_stripped_for_speech(self):
        from resonate.guide import _plain
        self.assertEqual(_plain("**nothing** can *separate* us"), "nothing can separate us")
        self.assertEqual(_plain("# Heading\n- point one\n- point two"), "Heading\npoint one\npoint two")
        self.assertNotIn("*", _plain("He said *come* to `me`"))

    def test_voice_flag_and_history_shape_are_accepted(self):
        out = self.guide.reply("I feel anxious tonight.", user_id="t_guide", voice=True,
                               history=[{"role": "user", "content": "long day"},
                                        {"role": "assistant", "content": "tell me more"}])
        self.assertTrue(out["ok"])
        self.assertTrue(out["reply"])

    def test_memory_graph_is_shared_across_surfaces(self):
        # the guide writes under the SAME user_id every surface uses — no prefix silo,
        # so the popup and the reels shelves see what Ezra heard (themes only)
        self.guide.reply("I'm so worried about money and I can't stop worrying.",
                         user_id="t_shared")
        tops = [t for t, _ in self.guide.engine.memory.patterns("t_shared").get("top_themes") or []]
        self.assertIn("anxiety", tops)


class TestRateLimiter(unittest.TestCase):
    def test_window_isolation_and_retry(self):
        from resonate.ratelimit import RateLimiter
        rl = RateLimiter({"b": (2, 60)})
        self.assertTrue(rl.allow("b", "u1"))
        self.assertTrue(rl.allow("b", "u1"))
        self.assertFalse(rl.allow("b", "u1"))        # third hit inside the window blocks
        self.assertTrue(rl.allow("b", "u2"))         # other users unaffected
        self.assertGreater(rl.retry_after("b", "u1"), 0)


class TestRefParse(unittest.TestCase):
    """Human references -> USFM: the path that lets Ezra answer 'quote me X'."""

    def _one(self, text):
        from resonate.refparse import find_references
        got = find_references(text)
        self.assertEqual(len(got), 1, "expected exactly one reference in %r" % text)
        return got[0]

    def test_common_forms(self):
        self.assertEqual(self._one("What does John 3:16 say?")["usfm"], "JHN.3.16")
        self.assertEqual(self._one("Read me Philippians 4:6-7")["usfm"], "PHP.4.6-PHP.4.7")
        self.assertEqual(self._one("Quote Psalm 23 verse 1")["usfm"], "PSA.23.1")
        self.assertEqual(self._one("psalm 23, please")["usfm"], "PSA.23")

    def test_numbered_books_and_roman_numerals(self):
        self.assertEqual(self._one("1 Peter 5:7")["usfm"], "1PE.5.7")
        self.assertEqual(self._one("I Peter 5:7")["usfm"], "1PE.5.7")
        self.assertEqual(self._one("1st John 4:18")["usfm"], "1JN.4.18")

    def test_aliases(self):
        self.assertEqual(self._one("Ps. 23:1")["usfm"], "PSA.23.1")
        self.assertEqual(self._one("Matt 6:34")["usfm"], "MAT.6.34")
        self.assertEqual(self._one("Song of Songs 2:1")["usfm"], "SNG.2.1")

    def test_multiple_and_dedup(self):
        from resonate.refparse import find_references
        got = find_references("compare 1 Peter 5:7 with Matt 6:34 and 1 Peter 5:7 again")
        self.assertEqual([g["usfm"] for g in got], ["1PE.5.7", "MAT.6.34"])

    def test_fake_books_and_plain_text_yield_nothing(self):
        from resonate.refparse import find_references
        self.assertEqual(find_references("the book of hezekiah 4 and 2 opinions 3:5"), [])
        self.assertEqual(find_references("no scripture here, just a hard week"), [])


class TestGuideDirectQuote(unittest.TestCase):
    """'What does John 3:16 say?' must ground and quote — never refuse (the one
    request a Scripture guide cannot fumble)."""

    def setUp(self):
        from resonate.guide import ScriptureGuide
        self.guide = ScriptureGuide(Engine(EngineConfig()))

    def test_direct_request_grounds_the_exact_verse(self):
        out = self.guide.reply("What does John 3:16 say?", user_id="t_quote")
        self.assertTrue(out["ok"])
        refs = [r["reference"] for r in out["refs"]]
        self.assertIn("John 3:16", refs)
        jhn = next(r for r in out["refs"] if r["reference"] == "John 3:16")
        self.assertIn("loved the world", jhn["text"])   # verbatim wording is in context
        self.assertIn("John 3:16", out["reply"])        # and the reply cites it

    def test_unverified_wording_never_enters_the_context(self):
        # a reference we have no licensed/sample text for -> placeholder -> excluded,
        # so the model can never 'quote' scaffolding text
        out = self.guide.reply("What does Habakkuk 3:17 say?", user_id="t_quote")
        self.assertTrue(out["ok"])
        for r in out["refs"]:
            self.assertNotIn("[", r["text"])

    def test_emotional_grounding_still_works_alongside(self):
        out = self.guide.reply("I'm anxious — what does 1 Peter 5:7 say?", user_id="t_quote")
        refs = [r["reference"] for r in out["refs"]]
        self.assertIn("1 Peter 5:7", refs)


class TestLiveFallbacks(unittest.TestCase):
    """Network loss must degrade (labelled fallback text), never drop the request."""

    def test_live_youversion_falls_back_offline(self):
        from resonate.providers.youversion import LiveYouVersion
        cfg = EngineConfig()
        cfg.yv_base_url = "http://127.0.0.1:9"       # closed port = instant refusal
        yv = LiveYouVersion(cfg)
        out = yv.fetch("JHN.3.16")
        self.assertEqual(out["source"], "offline-sample")   # public-domain sample text
        self.assertIn("loved the world", out["text"])
        out2 = yv.fetch("HAB.3.17")                  # nothing sampled -> honest placeholder
        self.assertEqual(out2["source"], "placeholder")

    def test_template_bridge_covers_every_tone(self):
        from resonate.providers.gloo import template_bridge
        from resonate.models import Beat
        beat = Beat(index=0, text="I can't keep up", themes=["weariness"],
                    emotion="exhausted", intensity=0.7)
        for tone in ("comfort", "assurance", "hope", "challenge", "celebration",
                     "conviction", "unknown-tone"):
            line = template_bridge(beat, {"reference": "Matthew 11:28", "tone": tone})
            self.assertIn("Matthew 11:28", line)


class TestPolicyPrecheck(unittest.TestCase):
    """precheck() is the read-only half of decide(): the server uses it to skip the
    whole LLM pipeline when silence is already certain (cooldown/budget/non-seam),
    so it must never consume budget or stamp state."""

    def _p(self):
        cfg = PolicyConfig(seams={"message"}, cooldown_seconds=90, max_per_session=2)
        t = {"now": 1000.0}
        return DeliveryPolicy(cfg, clock=lambda: t["now"]), t

    def test_precheck_never_mutates(self):
        p, _ = self._p()
        for _ in range(5):
            self.assertTrue(p.precheck("u", "message")["surface"])
        u = p._u("u")
        self.assertEqual((u.decisions, u.session_count), (0, 0))
        # a real decide afterwards behaves exactly as the first decision of the session
        self.assertTrue(p.decide("u", "message", confidence=0.9)["surface"])

    def test_precheck_honours_cooldown_and_budget(self):
        p, t = self._p()
        self.assertTrue(p.decide("u", "message", confidence=0.9)["surface"])   # stamps cooldown
        self.assertFalse(p.precheck("u", "message")["surface"])                # within cooldown
        t["now"] += 91
        self.assertTrue(p.precheck("u", "message")["surface"])                 # cooldown passed
        self.assertTrue(p.decide("u", "message", confidence=0.9)["surface"])   # session cap hit (2)
        t["now"] += 91
        self.assertFalse(p.precheck("u", "message")["surface"])                # cap enforced

    def test_precheck_rejects_non_seams_allows_manual(self):
        p, _ = self._p()
        self.assertFalse(p.precheck("u", "typing")["surface"])
        self.assertTrue(p.precheck("u", "manual")["surface"])


class TestPanelPreviewSync(unittest.TestCase):
    """web/panel-preview.html is a hand-kept snapshot of the extension panel. Its
    user-facing copy must match content.js — it drifted once ('processed locally ·
    nothing stored' survived a privacy-copy rewrite) and this pins it."""

    def test_footer_copy_matches_content_js(self):
        import re
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "integrations", "chatgpt-extension", "content.js"),
                  encoding="utf-8") as f:
            js = f.read()
        with open(os.path.join(root, "web", "panel-preview.html"), encoding="utf-8") as f:
            html = f.read()
        real = [m.replace("\\'", "'") for m in re.findall(r'class="foot">([^<]+)</div>', js)]
        shown = re.findall(r'class="foot">([^<]+)</div>', html)
        self.assertTrue(real, "no footer strings found in content.js")
        self.assertGreaterEqual(len(shown), 2, "panel-preview lost its footer lines")
        for s in shown:
            self.assertIn(s, real, "panel-preview footer drifted from content.js: %r" % s)


class TestPlainText(unittest.TestCase):
    def test_story_markdown_is_stripped_but_paragraphs_survive(self):
        from resonate.textutil import plain_text
        s = plain_text("You are **worn** and *weary*.\n\nRest — `selah`.", keep_newlines=True)
        self.assertNotIn("*", s)
        self.assertNotIn("`", s)
        self.assertIn("\n\n", s)

    def test_gravity_of_flat_grief_sentences(self):
        # "My dad died last week." carries no amplifier words — the gravity cue must
        # still read it as high-intensity so comfort-tone verses stay in range.
        from resonate.providers.gloo import lexicon_segment
        beats = lexicon_segment("My dad died last week.")
        self.assertTrue(beats)
        self.assertGreaterEqual(beats[0].intensity, 0.7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
