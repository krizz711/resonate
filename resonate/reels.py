"""Story-reel resolution — 'watch this verse's story'.

Each delivered verse can carry a reel_url: a short vertical story film of that verse
(realistic people, inner-voice narration — the format pitched for YouVersion or a
related platform to host). Curated/generated reels live in data/reels.json keyed by
usfm; anything without one falls back to the verse's own YouVersion page, so the
button always leads somewhere real and licensed.
"""
from __future__ import annotations

import json

from .config import DATA_DIR

# bible.com version ids for the "read more" fallback link (distinct from the
# Platform API's numeric bible_id, which live_check.py resolves separately).
_BIBLE_COM_VERSION = {"KJV": 1, "NIV": 111, "NIRV": 110, "ASV": 12, "WEB": 206}


def _first_usfm(usfm: str) -> str:
    """Range 'PHP.4.6-PHP.4.7' -> 'PHP.4.6' (bible.com anchors on a single verse)."""
    return (usfm or "").split("-")[0].strip()


class ReelStore:
    def __init__(self):
        p = DATA_DIR / "reels.json"
        try:
            self.reels = json.loads(p.read_text(encoding="utf-8")).get("reels", {})
        except OSError:
            self.reels = {}

    def resolve(self, usfm: str, translation: str = "KJV") -> dict:
        """-> {url, kind: 'story'|'verse-page', title?} — never empty."""
        entry = self.reels.get(usfm) or self.reels.get(_first_usfm(usfm))
        if entry and entry.get("url"):
            return {"url": entry["url"], "kind": "story", "title": entry.get("title", "")}
        ver = _BIBLE_COM_VERSION.get((translation or "KJV").upper(), 1)
        first = _first_usfm(usfm)
        return {"url": "https://www.bible.com/bible/%d/%s.%s" % (ver, first, (translation or "KJV").upper()),
                "kind": "verse-page", "title": ""}

    def groups_for(self, verse_store, beat_themes, context_themes=None,
                   translation: str = "KJV", per_group: int = 3) -> list:
        """Context -> prioritized reel sets: 'reels for you', in watch order.

        Priority 1  For this moment      — reels for the themes the person just named.
        Priority 2  Threads you return to — themes echoing through the conversation.
        Priority 3  Steady ground        — comfort/hope/peace staples, always worth keeping.

        Each group carries a one-line subtitle saying what it is for. Curated story
        reels rank before verse-page fallbacks inside a group; a verse never appears
        twice across groups. Groups with no reels are dropped, so callers can rely
        on every returned group having something to watch."""
        ctx = [t for t in (context_themes or []) if t not in set(beat_themes or [])]
        specs = [
            (1, "For this moment",
             "Because you spoke of %s." % ", ".join(beat_themes[:2]) if beat_themes else "Picked for what you just said.",
             beat_themes or []),
            (2, "Threads you return to",
             "This conversation kept touching %s." % ", ".join(ctx[:2]) if ctx else "Echoes from this conversation.",
             ctx),
            (3, "Steady ground",
             "Kept for moments like this — quiet anchors of comfort and hope.",
             ["comfort", "hope", "peace", "rest"]),
        ]
        groups, seen = [], set()
        for priority, title, subtitle, themes in specs:
            want = set(themes)
            if not want:
                continue
            matched = []
            for v in verse_store.verses:
                if v["reference"] in seen or not (want & set(v.get("themes", []))):
                    continue
                reel = self.resolve(v.get("usfm", ""), translation)
                matched.append({"reference": v["reference"], "usfm": v.get("usfm", ""),
                                "note": v.get("note", ""), **reel})
            matched.sort(key=lambda r: r["kind"] != "story")  # real story films first
            matched = matched[:per_group]
            if not matched:
                continue
            seen.update(r["reference"] for r in matched)
            groups.append({"priority": priority, "title": title,
                           "subtitle": subtitle, "reels": matched})
        return groups
