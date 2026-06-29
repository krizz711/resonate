# Resonate

**Scripture for the stories people are already telling.**

Resonate is a *living context engine* that sits between two APIs — **Gloo AI Studio**
(understanding) and the **YouVersion Platform API** (verified Scripture) — and delivers the
single best-fit verse for a moment, with memory of what came before so it never repeats and
reflects the person's ongoing journey.

Built for the Kaggle hackathon **Scripture in New Frontiers** (frontier: *creator tools*).
Submission due **2026-08-01**.

## How it works
The engine reads text (a transcript, a journal entry, a sentence), finds the emotional
"beats", matches each to a verse using semantic + thematic + tonal + memory signals, fetches
the **real** verse text live from YouVersion, and writes a one-line "bridge" connecting the
person's own words to the verse.

Full logic: see [ENGINE-DESIGN.md](ENGINE-DESIGN.md).

## Key design principles
1. **The LLM never quotes Scripture.** Gloo proposes a reference; YouVersion supplies the
   text. No hallucinated verses.
2. **Constrained, not freelancing.** Verses come from a vetted, theme-tagged shortlist
   (`data/verses.json`), ranked by a transparent fit score.
3. **Living, not reactive.** A per-user memory makes delivery aware of history and patterns.
4. **Safety first.** Crisis/self-harm beats are flagged to a human-help card, never
   auto-answered with a verse.

## Quickstart (offline — no keys, no installs)
The engine core runs on the Python standard library alone, with mock providers + local memory:

```bash
python scripts/demo.py
```

This runs the full pipeline end to end: it segments two "episodes" of a creator's transcript,
retrieves and ranks verses (hybrid dense + BM25 + tag, fused with RRF), re-ranks with the
per-user context graph (watch it avoid repeats and reflect the journey in episode 2), fetches
real verse text, writes a bridge line, and demonstrates the safety hold on a crisis input.

To use the real APIs later: `cp .env.example .env`, fill the keys, set `RESONATE_MODE=live`.

## Status
**Phase 0 complete** — offline engine core working (see [Resonate-Build-Plan.pdf](Resonate-Build-Plan.pdf)).
Next: wire in the live Gloo + YouVersion APIs (Phase 1, after the keys open on 2026-07-06).

## Layout
```
resonate/                 engine package
  config.py               settings, weights, mock/live + memory backend switches
  models.py               Beat dataclass
  embeddings.py           TF-IDF embedder (v0 dense retriever; swappable for sentence-transformers)
  verses.py               loads the curated shortlist + builds the index
  retrieval.py            hybrid retrieval: dense + BM25 + tags, fused with RRF
  memory.py               per-user context graph (local backend; Redis later)
  engine.py               the orchestrator (10 stages)
  providers/
    gloo.py               mock + live Gloo (segment, verify, bridge, safety)
    youversion.py         mock + live YouVersion (verified verse fetch)
data/
  verses.json             curated, theme-tagged verse shortlist (references + tags only)
  sample_texts.json       public-domain (KJV) text for the offline demo
scripts/demo.py           end-to-end offline demo
```
