# Resonate — competitiveness self-review

A frank assessment against the rubric (Impact & Vision 40 · Video & Storytelling 30 ·
Technical Depth 30). The goal: know exactly where we're strong and what would most raise the
score.

## Where we stand by criterion

### Impact & Vision — 40 pts  ·  strong
- Lands squarely in the organizers' own **"AI & digital assistants"** inspiration category, and
  matches their prompts almost verbatim (Scripture in conversations · recognize moments ·
  personalize over time · travel across AI tools · *discover Scripture without opening a Bible app*).
- Billions-scale reach: meets people inside ChatGPT, where the most vulnerable conversations of
  our time already happen.
- Directly satisfies the brief's hard tests: **not a Bible app**, **where people already are**,
  **not a pop-up** (restraint enforced in code).

### Video & Storytelling — 30 pts  ·  ready to shoot (script done, footage pending)
- A complete beat-by-beat script ([VIDEO-SCRIPT.md](VIDEO-SCRIPT.md)) with a built-in arc:
  vulnerable message → verse appears → silence on the ordinary → crisis routes to help → the
  **memory beat** ("returned to this 4× lately") → multi-surface + scale.
- The goosebumps moment (memory over time) is genuinely **built**, not mocked.
- ⛔ Needs the user to film/narrate (premium voice dub: Kokoro `af_bella`).

### Technical Depth — 30 pts  ·  strong, verifiable
- Hybrid retrieval (dense + BM25 + tags) fused with **RRF**; transparent fit score; per-user
  **temporal memory graph**; a **Delivery Policy** for restraint; phrasing-robust **safety gate**.
- **Anti-hallucination by construction**: model constrained to a vetted shortlist; YouVersion
  supplies the words.
- **Proof, not promises**: 31 unit tests + a 32-scenario eval harness (theme 100% / hit@1 96% /
  hit@3 100% / safety 100% / FP 0%) wired in as a regression guard.
- Three working surfaces from one engine; mock/live adapters; runs fully offline.

## Done vs. remaining
| | |
|---|---|
| ✅ Done | engine, 3 surfaces, restraint, safety, memory-over-time, voice, tests+eval, notebook, writeup, video script, cover, parchment UI |
| ⛔ Blocked | **live Gloo + YouVersion keys** (open 2026-07-06) — flip `RESONATE_MODE=live`; **filming the video** (human) |

## Top 3 things that would most raise the score
1. **Wire in the live APIs the moment keys drop (07-06).** It converts "well-engineered (mock)"
   into "genuinely functional" for the 30-pt Technical criterion, and lets real Gloo handle any
   phrasing (removing the offline lexicon's blind spots). *Highest leverage.*
2. **Shoot a tight, emotional 3-minute video.** 70% of the score is Impact + Storytelling, and
   the video is the primary lens. Protect the memory beat and the crisis-safety beat.
3. **Upgrade the dense retriever to real sentence-transformer embeddings.** Makes matching feel
   *magical* on unusual phrasings; measure the lift on the existing eval harness (target hit@1 ↑).

## Honest weaknesses (and the mitigations)
- *Offline matching is lexical* → real Gloo + dense embeddings fix this (items 1 & 3).
- *Browser-extension DOM can change* → scoped to one selector on one site; fails safe (never
  breaks the chat) if it changes.
- *Verse aptness isn't perfect* (one honest eval miss kept) → that's truthful; live reasoning improves it.

**Bottom line:** the vision is on-target and the engineering is real and verified. The remaining
gap to "winning" is execution the loop can't do alone — the live-API flip and a compelling video.
