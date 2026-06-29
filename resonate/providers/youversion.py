"""YouVersion Platform API provider — the ONLY source of verse text in the system.

MockYouVersion serves public-domain (KJV) sample text from data/sample_texts.json so the
offline demo shows real words; anything not cached returns a clearly-labelled placeholder.
LiveYouVersion fetches the licensed text by reference in Phase 1.
"""
from __future__ import annotations

import json

from ..config import DATA_DIR


class MockYouVersion:
    def __init__(self, config):
        self.config = config
        p = DATA_DIR / "sample_texts.json"
        self.cache = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def fetch(self, usfm, translation=None):
        translation = translation or self.config.translation
        entry = self.cache.get(usfm)
        if entry:
            return {"usfm": usfm, "translation": entry.get("translation", "KJV"),
                    "text": entry["text"], "source": "offline-sample"}
        return {"usfm": usfm, "translation": translation, "source": "placeholder",
                "text": "[%s %s] — fetched live from YouVersion when an app key is configured." % (translation, usfm)}


class LiveYouVersion:
    """Real YouVersion Platform API. Confirm exact endpoint/response shape in Phase 1."""

    def __init__(self, config):
        self.config = config

    def fetch(self, usfm, translation=None):
        import httpx
        url = "%s/bibles/%s/passages/%s" % (self.config.yv_base_url, self.config.bible_id, usfm)
        headers = {"X-YVP-App-Key": self.config.yv_app_key, "Accept": "application/json"}
        r = httpx.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        # NOTE: confirm the exact text field against the API docs during integration.
        text = data.get("content") or data.get("text") or ""
        return {"usfm": usfm, "translation": translation or self.config.translation,
                "text": text, "source": "youversion"}
