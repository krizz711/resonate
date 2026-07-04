"""'Your story' — a personal reflection woven from the user's conversation and ONE
vetted biblical narrative (stage 11, the generative centerpiece).

Anti-hallucination, same as verses: narratives come from a curated shortlist
(data/stories.json — references + our own reviewed synopses). The LLM (Gloo, live)
narrates the user's moment INTO that narrative; it never invents scripture. The only
verse text shown verbatim is the YouVersion-fetched verse the panel already holds,
and every story carries the label "a reflection inspired by <ref> — not Scripture."

Safety: stories are never composed for crisis input (the caller shows the help card
instead; compose() enforces it again as a backstop).
"""
from __future__ import annotations

import json
from collections import defaultdict, deque

from .config import DATA_DIR
from .providers.gloo import is_crisis


class StoryWeaver:
    def __init__(self, gloo):
        data = json.loads((DATA_DIR / "stories.json").read_text(encoding="utf-8"))
        self.stories = data["stories"]
        self.gloo = gloo
        self._recent = defaultdict(lambda: deque(maxlen=3))  # user -> last narrative ids

    # ---------------- selection ----------------
    def select(self, themes, ctx_themes=None, arc_themes=None, user_id="default"):
        """Pick the narrative whose themes best cover this moment.
        beat themes weigh 1.0, conversation context 0.5, recurring arcs 0.3;
        the user's last few narratives are penalized so stories don't repeat."""
        beat = set(themes or [])
        ctx = set(ctx_themes or [])
        arc = set(arc_themes or [])
        recent = set(self._recent[user_id])
        best, best_score = None, float("-inf")
        for s in self.stories:
            st = set(s["themes"])
            score = (1.0 * len(beat & st) + 0.5 * len(ctx & st) + 0.3 * len(arc & st)
                     - (1.5 if s["id"] in recent else 0.0))
            if score > best_score:
                best, best_score = s, score
        return best if best_score > 0 else None

    # ---------------- composition ----------------
    def compose(self, user_text, beat_themes, narrative, verse, user_id="default",
                emotion="", memory_note=None):
        """-> {title, reference, usfm, text, label, narrative_id} or raises ValueError.
        `verse` = the already-delivered payload: {reference, verse_text, translation}."""
        if is_crisis(user_text or ""):
            raise ValueError("stories are never composed for crisis input")
        if narrative is None:
            raise ValueError("no fitting narrative")
        text = self.gloo.story(user_text, emotion or "", narrative, verse, memory_note)
        self._recent[user_id].append(narrative["id"])
        return {
            "title": narrative["title"],
            "reference": narrative["reference"],
            "usfm": narrative["usfm"],
            "text": text,
            "verse_reference": verse.get("reference", ""),
            "label": "A reflection inspired by %s — not Scripture. Verse text: %s (%s), via YouVersion."
                     % (narrative["reference"], verse.get("reference", ""),
                        verse.get("translation", "KJV")),
            "narrative_id": narrative["id"],
        }
