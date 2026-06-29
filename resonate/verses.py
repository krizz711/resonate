"""Loads the curated verse shortlist and builds its semantic index (stages 2-3)."""
from __future__ import annotations

import json

from .config import DATA_DIR
from .embeddings import LexicalEmbedder


class VerseStore:
    def __init__(self):
        data = json.loads((DATA_DIR / "verses.json").read_text(encoding="utf-8"))
        self.verses = data["verses"]
        self.theme_vocab = data.get("theme_vocab", [])

        # Each verse gets a text "profile" from its tags/keywords/note (NOT the verse text,
        # which we never store — it's fetched live from YouVersion).
        for v in self.verses:
            v["_profile"] = " ".join(v.get("keywords", []) + v.get("themes", []) + [v.get("note", "")])

        self.embedder = LexicalEmbedder([v["_profile"] for v in self.verses])
        for v in self.verses:
            v["_vec"] = self.embedder.embed(v["_profile"])

    def embed_query(self, text: str) -> dict:
        return self.embedder.embed(text)
