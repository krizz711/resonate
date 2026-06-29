"""Semantic layer (stage 2).

v0 uses a dependency-free TF-IDF lexical embedding so the whole engine runs on the Python
standard library alone. The interface (`embed` -> sparse dict, `cosine`) is deliberately the
same one a real sentence-transformer backend would expose, so upgrading the semantic quality
later is a drop-in change with no engine edits.
"""
from __future__ import annotations

import math
import re
from collections import Counter

_STOP = set(
    "a an the and or but if then of to in into on at for with is are am was were be been being "
    "i you he she it we they me my your our his her their this that these those as so just really "
    "very feel feels feeling felt like dont im can im not no yes do does did have has had will would "
    "about it's i'm don't can't cant got get there here what when".split()
)


def tokenize(text: str) -> list:
    return [t for t in re.findall(r"[a-z']+", text.lower()) if t not in _STOP and len(t) > 1]


class LexicalEmbedder:
    def __init__(self, corpus: list):
        self.df = Counter()
        docs = [tokenize(c) for c in corpus]
        for d in docs:
            for tok in set(d):
                self.df[tok] += 1
        self.n_docs = max(1, len(docs))

    def _idf(self, tok: str) -> float:
        return math.log((self.n_docs + 1) / (self.df.get(tok, 0) + 1)) + 1.0

    def embed(self, text: str) -> dict:
        toks = tokenize(text)
        if not toks:
            return {}
        tf = Counter(toks)
        return {t: (c / len(toks)) * self._idf(t) for t, c in tf.items()}


def cosine(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0
