"""The orchestrator — wires the 10 pipeline stages together (see ENGINE-DESIGN.md)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .config import EngineConfig
from .guardian import GuardianAlerts
from .verses import VerseStore
from .retrieval import HybridRetriever
from .memory import make_memory
from .providers import make_gloo, make_youversion
from .providers.gloo import lexicon_segment, LEXICON

SAFETY_MESSAGE = (
    "This sounds heavy, and a verse isn't the right response here. Please reach out to someone "
    "you trust or a crisis line — e.g. India: AASRA +91-98204 66726, iCall +91-91529 87821; "
    "US: call or text 988. You matter, and you don't have to carry this alone."
)


def _tone_fit(beat, verse) -> float:
    """Reward verses whose intensity_fit range contains the beat's intensity (1.0), with a
    falloff outside it. A high-intensity grief beat should get comfort, not 'rejoice!'."""
    lo, hi = verse.get("intensity_fit", [0.0, 1.0])
    if lo <= beat.intensity <= hi:
        return 1.0
    d = (lo - beat.intensity) if beat.intensity < lo else (beat.intensity - hi)
    return max(0.0, 1.0 - 2.0 * d)


def _theme_cover(beat, verse) -> float:
    """How much of the beat's themes the verse addresses (recall-oriented, high-precision)."""
    b = set(beat.themes)
    if not b:
        return 0.0
    return len(b & set(verse.get("themes", []))) / len(b)


class ThemeGaps:
    """Tallies the theme labels the engine could NOT answer — the segmenter's
    'other:<feeling>' escape hatch, or any tag outside the vocabulary. This is how
    the corpus learns where to grow next (surfaced on /health): the LLM scouts the
    gap, a human vets the verses, the node ships. Privacy: stores ONLY sanitized
    labels and counts — never the person's words."""

    _MAX_LABELS = 200  # a rogue model can't grow the file without bound

    def __init__(self, config):
        self._persist_on = getattr(config, "gaps_persist", False)
        self._path = Path(getattr(config, "gaps_path", "") or "")
        self._counts = {}
        if self._persist_on:
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                self._counts = {str(k): int(v) for k, v in raw.items()}
            except (OSError, ValueError):
                self._counts = {}

    @staticmethod
    def _label(theme):
        t = str(theme or "").lower().strip()
        if t.startswith("other:"):
            t = t[6:]
        t = re.sub(r"[^a-z0-9 _-]", "", t).strip()[:32]
        return "" if t in ("", "other") else t

    def record(self, themes):
        for t in themes or []:
            lab = self._label(t)
            if not lab or (lab not in self._counts and len(self._counts) >= self._MAX_LABELS):
                continue
            self._counts[lab] = self._counts.get(lab, 0) + 1
        self._save()

    def top(self, n=8):
        ranked = sorted(self._counts.items(), key=lambda x: x[1], reverse=True)
        return [{"theme": t, "count": c} for t, c in ranked[:n]]

    def _save(self):
        if not self._persist_on:
            return
        try:
            tmp = str(self._path) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._counts, f, ensure_ascii=False)
            os.replace(tmp, str(self._path))
        except OSError:
            pass


class Engine:
    def __init__(self, config=None):
        self.config = config or EngineConfig()
        self.verses = VerseStore()
        self.retriever = HybridRetriever(self.verses, rrf_k=self.config.rrf_k)
        self.gloo = make_gloo(self.config)
        self.yv = make_youversion(self.config)
        self.memory = make_memory(self.config)
        self.guardian = GuardianAlerts(self.config)
        # every theme the system can actually speak to — segmentation vocabulary plus
        # the corpus's own tags; beats outside this set abstain in resonate() below
        self._known_themes = set(LEXICON) | set(self.verses.theme_vocab)
        self.gaps = ThemeGaps(self.config)  # what people felt that we couldn't answer

    def _history_themes(self, history) -> list:
        """Themes heard in the last few prior messages, most recent counted twice.
        Compact, high-signal conversation context — raw history text never joins the
        query (a long old message would drown the present moment).

        History is segmented with the free LEXICON, never the live model: these
        themes only nudge retrieval, and re-annotating already-seen messages cost
        up to history_max extra LLM round-trips on EVERY /resonate (measured as
        the bulk of live panel latency). The current message still gets the full
        live treatment in resonate() below."""
        themes = []
        if not history:
            return themes
        recent = [h for h in history if isinstance(h, str) and h.strip()]
        recent = recent[-self.config.history_max:]
        for age, h in enumerate(reversed(recent)):  # age 0 = the message just before this one
            for b in lexicon_segment(h):
                for t in b.themes:
                    themes.extend([t, t] if age == 0 else [t])
        return themes

    def resonate(self, text, user_id: str = "demo", history=None) -> dict:
        """history: prior user messages (oldest -> newest), OPTIONAL. They never trigger a
        verse by themselves and never enter the safety decision (each was safety-checked
        when it arrived); they only sharpen WHICH verse fits the conversation."""
        episode = self.memory.start_episode(user_id)

        # stage 6 — safety gate FIRST, on the raw text, independent of segmentation, so a crisis
        # is never missed (and never answered with a verse) even if no theme was detected.
        if self.gloo.safety_text(text):
            return {"user_id": user_id, "episode": episode,
                    "deliveries": [{"status": "safety_hold",
                                    "beat": {"text": text, "themes": [], "emotion": "in distress", "intensity": 0.95},
                                    "message": SAFETY_MESSAGE,
                                    "guardian": self.guardian.alert(user_id)}],
                    "series_memory": self.memory.patterns(user_id)}

        ctx_themes = self._history_themes(history)
        beats = self.gloo.segment(text)
        deliveries = []

        for beat in beats:
            # per-beat backstop (a transcript could carry a crisis sentence mid-way)
            if self.gloo.safety(beat):
                deliveries.append({"status": "safety_hold", "beat": vars(beat), "message": SAFETY_MESSAGE,
                                   "guardian": self.guardian.alert(user_id)})
                continue

            # vocabulary honesty — a beat whose themes are ALL outside the known
            # vocabulary (the live model's "other" escape hatch) must abstain: forcing
            # the nearest axis delivers a confident wrong verse (pride→doubt, observed
            # live 2026-07-16). Honest silence over a shoehorned match.
            if not any(t in self._known_themes for t in beat.themes):
                self.gaps.record(beat.themes)  # labels only — the corpus growth signal
                deliveries.append({"status": "abstain", "beat": vars(beat),
                                   "message": "This moment's theme isn't one Resonate can speak to yet."})
                continue

            # stage 3 — hybrid retrieve + RRF (conversation context echoes into the query)
            candidates = self.retriever.retrieve(beat, topk=self.config.topk,
                                                 context_themes=ctx_themes)
            if not candidates:
                deliveries.append({"status": "abstain", "beat": vars(beat),
                                   "message": "No confident verse match for this beat."})
                continue

            # stage 4 — memory re-rank + tone fit
            w = self.config.weights
            max_rrf = max(c["rrf"] for c in candidates) or 1.0
            scored = []
            for c in candidates:
                v = c["verse"]
                norm_rrf = c["rrf"] / max_rrf
                cover = _theme_cover(beat, v)
                tone = _tone_fit(beat, v)
                rec = self.memory.recency_penalty(user_id, v["reference"])
                fat = self.memory.theme_fatigue(user_id, v.get("themes", []))
                arc = self.memory.narrative_continuity(user_id, v.get("themes", []))
                final = (w.rrf * norm_rrf + w.theme * cover + w.tone * tone
                         - w.recent * rec - w.repeat * fat + w.arc * arc)
                scored.append({
                    "verse": v, "final": final, "ranks": c["ranks"],
                    "components": {"rrf": round(norm_rrf, 3), "theme": round(cover, 3),
                                   "tone": round(tone, 3), "recency_pen": round(rec, 3),
                                   "fatigue": round(fat, 3), "narrative": round(arc, 3)},
                })
            scored.sort(key=lambda x: x["final"], reverse=True)

            # stage 7 — confidence / abstention (confidence = top fit vs. the best possible)
            top = scored[0]
            confidence = round(top["final"] / (w.rrf + w.theme + w.tone + w.arc), 3)
            low_conf = confidence < 0.55

            # stage 5 — LLM verify/select, constrained to the top candidates
            chosen_verse, rationale = self.gloo.verify(beat, [s["verse"] for s in scored[:4]])
            chosen = next((s for s in scored if s["verse"]["reference"] == chosen_verse["reference"]), top)
            v = chosen["verse"]

            # stage 8 — verified fetch (YouVersion) ; stage 9 — bridge
            fetched = self.yv.fetch(v["usfm"], self.config.translation)
            bridge = self.gloo.bridge(beat, v, fetched["text"])

            # stage 10 — remember
            self.memory.add(user_id, beat.themes, beat.intensity, v["reference"], episode=episode)

            # series memory: surface a recurring-theme note (the "you've returned to this" moment)
            primary = beat.themes[0] if beat.themes else None
            mem_note = None
            if primary:
                n = self.memory.theme_count(user_id, primary)
                if n >= 3:
                    mem_note = "You've returned to %s — %d× lately." % (primary, n)

            deliveries.append({
                "status": "delivered", "beat": vars(beat), "memory_note": mem_note,
                "reference": v["reference"], "usfm": v["usfm"], "tone": v.get("tone"),
                "translation": fetched["translation"], "verse_text": fetched["text"],
                "text_source": fetched["source"], "bridge": bridge, "rationale": rationale,
                "final": round(chosen["final"], 3), "confidence": confidence, "low_confidence": low_conf,
                "components": chosen["components"], "ranks": chosen["ranks"],
                "alternatives": [{"reference": s["verse"]["reference"], "final": round(s["final"], 3)}
                                 for s in scored[1:4]],
            })

        return {"user_id": user_id, "episode": episode, "deliveries": deliveries,
                "series_memory": self.memory.patterns(user_id),
                "context": {"history_messages": len(history or []),
                            "themes": sorted(set(ctx_themes))}}
