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


_TAG_RE = None


def _strip_html(s: str) -> str:
    """The /passages endpoint returns HTML by default (<p>, <span> markers); we ask for
    format=text but strip defensively in case a deployment ignores the parameter."""
    global _TAG_RE
    if _TAG_RE is None:
        import re
        _TAG_RE = re.compile(r"<[^>]+>")
    import html as _html
    return _html.unescape(_TAG_RE.sub(" ", s or "")).replace("\xa0", " ").strip()


class LiveYouVersion:
    """Real YouVersion Platform API, per developers.youversion.com (verified 2026-07-04):

      GET {base}/bibles/{bible_id}/passages/{USFM}?format=text
      header  X-YVP-App-Key: <app key from platform.youversion.com>

    Field notes: the Bible must have its license agreement ACCEPTED on
    platform.youversion.com before it can be fetched; /v1/bibles listing requires
    language_ranges[] (ISO 639-3, literal brackets) and hides non-provisioned
    versions unless all_available=true. Verse text is HTML unless format=text.
    Fetched texts are cached in-memory for the process lifetime."""

    def __init__(self, config):
        self.config = config
        self._cache = {}

    def _get(self, usfm):
        import httpx
        url = "%s/bibles/%s/passages/%s" % (self.config.yv_base_url, self.config.bible_id, usfm)
        return httpx.get(url, params={"format": "text"},
                         headers={"X-YVP-App-Key": self.config.yv_app_key,
                                  "Accept": "application/json"}, timeout=30)

    def list_bibles(self, language="eng", all_available=True):
        """Discover version ids available to this app key (helper for setup/preflight)."""
        import httpx
        r = httpx.get("%s/bibles" % self.config.yv_base_url,
                      params={"language_ranges[]": language,
                              "all_available": str(bool(all_available)).lower()},
                      headers={"X-YVP-App-Key": self.config.yv_app_key,
                               "Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        return r.json()

    def fetch(self, usfm, translation=None):
        translation = translation or self.config.translation
        if usfm in self._cache:
            return self._cache[usfm]
        r = self._get(usfm)
        if r.status_code >= 400 and "-" in usfm:
            # some deployments reject full-range refs — fall back to the first verse
            r = self._get(usfm.split("-")[0])
        r.raise_for_status()
        data = r.json()
        text = data.get("content") or data.get("text") or ""
        if "<" in text:
            text = _strip_html(text)
        out = {"usfm": usfm, "translation": data.get("abbreviation", translation),
               "text": text.strip(), "source": "youversion"}
        self._cache[usfm] = out
        return out
