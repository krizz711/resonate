"""The orchestrator — wires the 10 pipeline stages together (see ENGINE-DESIGN.md)."""
from __future__ import annotations

from .config import EngineConfig
from .verses import VerseStore
from .retrieval import HybridRetriever
from .memory import make_memory
from .providers import make_gloo, make_youversion

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


class Engine:
    def __init__(self, config=None):
        self.config = config or EngineConfig()
        self.verses = VerseStore()
        self.retriever = HybridRetriever(self.verses, rrf_k=self.config.rrf_k)
        self.gloo = make_gloo(self.config)
        self.yv = make_youversion(self.config)
        self.memory = make_memory(self.config)

    def resonate(self, text, user_id: str = "demo") -> dict:
        episode = self.memory.start_episode(user_id)

        # stage 6 — safety gate FIRST, on the raw text, independent of segmentation, so a crisis
        # is never missed (and never answered with a verse) even if no theme was detected.
        if self.gloo.safety_text(text):
            return {"user_id": user_id, "episode": episode,
                    "deliveries": [{"status": "safety_hold",
                                    "beat": {"text": text, "themes": [], "emotion": "in distress", "intensity": 0.95},
                                    "message": SAFETY_MESSAGE}],
                    "series_memory": self.memory.patterns(user_id)}

        beats = self.gloo.segment(text)
        deliveries = []

        for beat in beats:
            # per-beat backstop (a transcript could carry a crisis sentence mid-way)
            if self.gloo.safety(beat):
                deliveries.append({"status": "safety_hold", "beat": vars(beat), "message": SAFETY_MESSAGE})
                continue

            # stage 3 — hybrid retrieve + RRF
            candidates = self.retriever.retrieve(beat, topk=self.config.topk)
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
                "series_memory": self.memory.patterns(user_id)}
