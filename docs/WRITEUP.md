# Resonate — Scripture, where you already are

**Subtitle:** A privacy-first companion that weaves *verified* Scripture into the AI conversations people already have — quietly, safely, only when it fits.

> Kaggle writeup (well under the 500-word limit). Running LIVE against both challenge APIs
> since keys opened 2026-07-06 — every claim below is exercised by the test suite.

---

**The problem.** Billions now type their most honest words — grief, burnout, doubt — into AI chatbots, not a Bible app. Scripture has never been present there. Resonate is the bridge: a browser extension beside ChatGPT that surfaces the verse your own words were already echoing, as a small dismissible parchment panel — no transcript kept, only theme patterns on your own machine.

**A context engine between the two APIs.**
- **Gloo AI Studio** tags the message's emotional *beats* (grief, perseverance, anxiety…), writes the one-line *bridge* to the verse, and runs safety classification — never reciting Scripture itself.
- **The engine** (our contribution) matches each beat with **hybrid retrieval** — dense embeddings + BM25 + theme tags fused via **Reciprocal Rank Fusion** — then re-ranks by tone-fit and a per-user **temporal memory graph** (recency, theme-fatigue, narrative continuity). It is **conversation-aware**: recent-message themes echo into retrieval — a money-worry chat gets *"my God shall supply all your need"*, not a generic anxiety verse; context sharpens *which* verse, never *whether* to speak.
- **YouVersion Platform API** returns the verified, licensed text. The model proposes a reference from a vetted shortlist; YouVersion supplies the words, so nothing is hallucinated.

**Native, not a pop-up.** A **Delivery Policy** decides whether to speak at all: silent on ordinary messages, firing only on a real, high-confidence beat, rate-limited, learning from dismissals. The panel itself practices restraint — after a few quiet seconds it **folds into a small wax seal**, never squatting on the user's space. Crisis messages are caught on the raw text by a phrasing-robust classifier and routed to a **human-help card — never a verse** (100% recall). Over weeks it notices recurring themes — *"you've returned to this 4× lately"* — personalization across conversations, not one sentence.

**Built for trust.** Only the user's own message is read, locally, opt-in per site. Three locally-synthesized **chapel voices** (Bella, Isabella, George) — tuned unhurried and reverent — can read each verse aloud, optionally by default. Each verse links onward to **"watch this verse's story"**, a reel format pitched for YouVersion to host.

**Engineering & verification.** The engine ships with a **90-case unit suite** and a **32-scenario evaluation harness** — theme recall 100%, verse hit@3 100%, **safety recall 100%, false-positives 0%** — wired in as a regression guard. Every external call sits behind a **mock/live adapter**, so it runs fully offline in development and flips to live APIs with one config change. The *same engine* also ships as an **MCP server** — Claude, ChatGPT or Gemini can call `resonate_verse` and `generate_story` natively, guarantees enforced server-side — plus VS Code and Discord surfaces: *you choose where Scripture meets you.*

**Challenges.** The hard parts weren't fetching a verse; they were **restraint** (most "verse generators" annoy — ours measures and enforces silence), **safety robustness** (a crisis must never be missed or answered with a verse), and **anti-hallucination** (constraining the model to a vetted set plus verified retrieval).

Resonate makes Scripture present where life actually happens — on the user's terms, never intruding.
