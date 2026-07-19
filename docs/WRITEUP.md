# Resonate — Scripture, where you already are

**Subtitle:** A privacy-first companion that weaves *verified* Scripture into the AI conversations people already have — quietly, safely, only when it fits.

---

**The problem.** Billions type their most honest words — grief, burnout, doubt — into AI chatbots, not a Bible app, and Scripture has never been present there. Resonate is the bridge: a browser extension beside ChatGPT that surfaces the verse your words already echoed, as a small dismissible parchment panel — no transcript kept, only theme patterns, on your machine.

**A context engine between the two APIs.**
- **Gloo AI Studio** tags the message's emotional *beats* (grief, perseverance, anxiety…) and writes the one-line *bridge* to the verse — never reciting Scripture itself.
- **The engine** (our contribution) matches each beat with **hybrid retrieval** — TF-IDF vectors + BM25 keyword search + theme tags fused via **Reciprocal Rank Fusion** — then re-ranks by tone-fit and a per-user **temporal memory graph** (recency, theme-fatigue, narrative continuity). It is **conversation-aware**: recent themes echo into retrieval, so a money-worry chat gets *"my God shall supply all your need,"* not a generic anxiety verse — sharpening *which* verse, never *whether* to speak.
- **YouVersion Platform API** returns the verified, licensed text. The model proposes a reference from a vetted shortlist; YouVersion supplies the words, so nothing is hallucinated.

**Native, not a pop-up.** A **Delivery Policy** decides whether to speak at all: silent on ordinary messages, firing only on a real, high-confidence beat, rate-limited, learning from dismissals. The panel practices restraint too — after a few quiet seconds it **folds into a small wax seal**. Crisis messages are caught on the raw text by a phrasing-robust classifier and routed to a **human-help card — never a verse**. Over weeks it notices recurring themes — *"you've returned to this 4× lately"* — memory across conversations, not one reply.

**Built for trust.** Only the user's own message is read, locally, opt-in per site. Three locally-synthesized **chapel voices** (Bella, Isabella, George) can read each verse aloud, optionally by default. Each verse links onward to **"watch this verse's story"** — a reel format pitched for YouVersion to host.

**Engineering & verification.** The engine ships with a **98-case unit suite** and a **42-scenario evaluation harness** — theme recall 100%, verse hit@3 100%, **safety recall 100% (14 crisis phrasings), false-positives 0%** — wired in as a regression guard. Every external call sits behind a **mock/live adapter** — fully offline, live with one config change. The *same engine* also ships as an **MCP server** — Claude, ChatGPT or Gemini call `resonate_verse` and `generate_story` natively, guarantees enforced server-side — so one context follows the user to any assistant.

**Challenges.** The hard parts weren't fetching a verse; they were **restraint** (measuring and enforcing silence, where most "verse generators" only annoy), **safety robustness** (a crisis must never be answered with a verse), and **anti-hallucination** (a vetted shortlist plus verified retrieval).

Resonate makes Scripture present where life actually happens — on the user's terms, never intruding.
