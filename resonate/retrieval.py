"""Hybrid retrieval (stage 3): dense + sparse + tag retrievers fused with RRF.

Three independent retrievers each rank the verse shortlist; their *ranks* (not raw scores)
are merged with Reciprocal Rank Fusion, which is robust because it needs no score calibration
across retrievers. v0's "dense" retriever is the TF-IDF embedder from embeddings.py; Phase 2
swaps in a sentence-transformer behind the same interface.
"""
from __future__ import annotations

import math
from collections import Counter

from .embeddings import tokenize, cosine


class BM25:
    """Standard Okapi BM25 over the verse profiles (the sparse retriever)."""

    def __init__(self, docs_tokens, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.N = len(docs_tokens)
        self.tf = [Counter(toks) for toks in docs_tokens]
        self.doclen = [len(toks) for toks in docs_tokens]
        self.avgdl = (sum(self.doclen) / self.N) if self.N else 0.0
        df = Counter()
        for toks in docs_tokens:
            for t in set(toks):
                df[t] += 1
        self.idf = {t: math.log(1 + (self.N - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def scores(self, query_tokens) -> list:
        out = []
        for i in range(self.N):
            tf, dl, s = self.tf[i], self.doclen[i], 0.0
            for q in query_tokens:
                f = tf.get(q, 0)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * dl / self.avgdl) if self.avgdl else 1.0
                s += self.idf.get(q, 0.0) * (f * (self.k1 + 1)) / denom
            out.append(s)
        return out


def rank_indices(scores) -> list:
    """Indices sorted by score descending (stable for ties)."""
    return [i for i, _ in sorted(enumerate(scores), key=lambda x: x[1], reverse=True)]


def rrf_fuse(rankings, k: int = 60) -> Counter:
    """Reciprocal Rank Fusion:  RRF(v) = sum over retrievers of 1 / (k + rank(v))."""
    fused = Counter()
    for ranking in rankings:
        for rank, idx in enumerate(ranking):  # rank is 0-based
            fused[idx] += 1.0 / (k + rank + 1)
    return fused


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


class HybridRetriever:
    def __init__(self, verse_store, rrf_k: int = 60):
        self.vs = verse_store
        self.rrf_k = rrf_k
        self.verses = verse_store.verses
        self.bm25 = BM25([tokenize(v["_profile"]) for v in self.verses])

    def retrieve(self, beat, topk: int = 12, context_themes=None) -> list:
        """context_themes: themes heard earlier in the conversation (recency-weighted by
        repetition). They join the query as extra tokens and echo into the tag retriever
        at half weight, so the verse choice follows the conversation, not one message —
        while the beat itself still decides WHETHER we speak at all."""
        ctx = list(context_themes or [])
        qtext = beat.text + " " + " ".join(beat.themes)
        if ctx:
            qtext = qtext + " " + " ".join(ctx)
        qtokens = tokenize(qtext)
        qvec = self.vs.embed_query(qtext)
        bthemes = set(beat.themes)
        ctxset = set(ctx)

        dense = [cosine(qvec, v["_vec"]) for v in self.verses]
        sparse = self.bm25.scores(qtokens)
        tag = [_jaccard(bthemes, set(v.get("themes", []))) +
               (0.5 * _jaccard(ctxset, set(v.get("themes", []))) if ctxset else 0.0)
               for v in self.verses]

        rankings = [rank_indices(dense), rank_indices(sparse), rank_indices(tag)]
        fused = rrf_fuse(rankings, self.rrf_k)
        rank_of = [{idx: r for r, idx in enumerate(rk)} for rk in rankings]

        items = []
        for idx, score in fused.most_common(topk):
            items.append({
                "verse": self.verses[idx],
                "rrf": score,
                "ranks": {"dense": rank_of[0][idx] + 1, "sparse": rank_of[1][idx] + 1, "tag": rank_of[2][idx] + 1},
                "raw": {"dense": round(dense[idx], 3), "sparse": round(sparse[idx], 3), "tag": round(tag[idx], 3)},
            })
        return items
