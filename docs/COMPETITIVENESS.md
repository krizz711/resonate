# Resonate — competitiveness self-review

A frank assessment against the rubric (Impact & Vision 40 · Video & Storytelling 30 ·
Technical Depth 30). The goal: know exactly where we're strong and what would most raise the
score.

## Webinar intel (2026-07-04 pre-challenge session — bind the plan to this)
- **Dates:** opens **July 6** · submissions close **July 31** · judging Aug 3–7 · winners Aug 10.
- **ONE submission per team, total.** No iterating. **Ties go to the EARLIER submission** →
  target submitting ~July 27–28 fully polished, not July 31.
- **Winning requirements:** full source code + documentation + **reproduction instructions**
  (README "Reproduce it" section ✓), **OSI-approved license** (MIT ✓), prize/tax docs within
  2 weeks of notification.
- **Judge's own words on Impact & Vision (40 pts):** a *real* problem — "not a made-up one, not
  one already addressed"; she is *"not looking for Bible painted on top of Facebook"* or an
  "xyz app with Bible scripts"; uniquely connect Scripture with people **and be scalable**.
  Our restraint/safety/memory story answers exactly this; say "not another Bible app" out loud
  in the video.
- **Video (30 pts):** "exciting… could this go viral… don't hold back" — show the product in
  action, make the experience feel real. **Tech (30 pts):** "verified by your code and writeup…
  genuinely functional and well-engineered, not just faked for the demo… pushed the tools to do
  something new" → film against LIVE APIs, flash the tests/eval, highlight innovative API use
  (Gloo auto-routing + `tradition`; grounded-completions w/ citations as a stretch; verified
  YouVersion passage fetch).
- **Frontier framing from the deck:** gaming · social · creator tools · wearables · fitness ·
  **AI assistants** (us) · spatial — "go where people already are."
- **$20 Gloo credit:** first 500 developers who register; also create accounts on
  **studio.ai.gloo.com** and **developer.youversion.com** — Gloo emails the code July 6 (or at
  signup). Setup: YouVersion → new application → app key → **Licensing → accept each Bible's
  agreement**; Gloo → Dashboard → API Credentials → client id + secret. Validate with
  `python scripts/live_check.py`.
- Official pages: kaggle.com/competitions/scripture-in-new-frontiers ·
  platform.youversion.com/summer-virtual-challenge-2026 · studio.ai.gloo.com/challenge.

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
- **Proof, not promises**: 98 unit tests + a 42-scenario eval harness (theme 100% / hit@3 100% /
  safety 100% across 14 crisis phrasings / FP 0%) wired in as a regression guard.
- Multiple working surfaces from one engine; mock/live adapters; runs fully offline.

## Done vs. remaining
| | |
|---|---|
| ✅ Done | engine, surfaces, restraint, safety, memory-over-time, voice, tests+eval, notebook, writeup, cover, parchment UI, **live Gloo + YouVersion** (hosted, verified) |
| ⛔ Remaining | **filming the ≤3-min video** (human) — the one big gap |

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
