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
