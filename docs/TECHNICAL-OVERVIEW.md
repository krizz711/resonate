# Resonate — Detailed Technical Overview

*A source document for a technical explainer. Resonate is an entry in the Kaggle "Scripture in New Frontiers" hackathon (frontier: AI and digital assistants), built on the YouVersion Platform API and the Gloo AI Studio API. It is MIT-licensed and runs live at https://resonate-hg6j.onrender.com.*

---

## 1. What Resonate Is, In One Paragraph

Resonate is a **context engine** that places *verified* Scripture inside the AI conversations people are already having — a quiet, dismissible verse that appears beside ChatGPT, or a Scripture capability that any AI assistant (Claude, Cursor, Gemini) can call natively. It is deliberately *not* another Bible app and *not* a verse-spamming bot. Its entire value is in three hard problems solved together: knowing **which** verse fits a human moment, knowing **whether** to speak at all, and guaranteeing the verse text is real and never hallucinated. The engine sits between two APIs — Gloo AI Studio (a faith-aligned language model) and the YouVersion Platform API (the source of licensed Scripture text) — and orchestrates a ten-stage pipeline that turns a raw, messy human message into a fitting, verified verse with a one-line bridge, or into silence, or, in a crisis, into a human-help card and never a verse.

---

## 2. The Problem

Billions of people now type their most honest words — grief, burnout, doubt, fear — into AI chatbots rather than into a Bible app. These are exactly the moments Scripture has spoken to for millennia, yet in that digital space it has never been present in any meaningful way. The two obvious ways to fix this are both wrong:

- **A separate Bible app** requires the person to *leave* the moment and go look something up. Nobody does that in the middle of a hard conversation.
- **A verse-spamming bot** recites Scripture at everything, frequently hallucinates the wording of verses, and — most dangerously — can respond to a person in crisis with a cheerful verse instead of help.

Resonate is the missing middle: present where life actually happens, restrained enough to be welcome rather than annoying, and verified enough to be trusted. The competition brief explicitly warns against building "another Bible app" or "the Bible painted on top of Facebook." Resonate answers that by being a *delivery layer* — you don't come to Resonate to read Scripture; you tell it (implicitly, through your own words) where you already are, and it meets you there.

---

## 3. Four Design Principles (Each Enforced in Code)

Every architectural decision in Resonate traces back to one of four commitments, and each is enforced by actual code rather than merely claimed:

1. **Native.** The verse appears *inside* your existing AI surface — a small parchment panel in ChatGPT, or a tool your model calls — not a destination you visit.
2. **Verified.** The language model *never recites Scripture*. It proposes a verse *reference*; the YouVersion Platform API supplies the actual words. Nothing is hallucinated.
3. **Restrained.** The engine stays silent on ordinary messages, speaks only on a real, high-confidence emotional beat, rate-limits itself, and learns from being dismissed.
4. **Safe.** Crisis text is caught on the raw input, before anything else, and routed to a human-help card — never a verse. This check is deterministic and runs on every surface.

---

## 4. System Architecture

Resonate is organized as three layers around a single engine.

**The delivery surfaces** are the native contexts where a person encounters Scripture. The flagship is a Chrome browser extension that injects a quiet verse panel beside ChatGPT. Alongside it: a Model Context Protocol (MCP) server so any AI assistant can call Scripture as a native tool; "Ezra," a conversational Scripture guide you can chat with or voice-call; a "Reels for you" page of verse-matched story films; and connectors for VS Code and Discord. Crucially, these are not five separate products — they are five thin surfaces over one shared engine.

**The Resonate Context Engine** is the core. It is written in pure Python standard library (no heavy framework dependencies for the core logic), which means it runs fully offline with mock providers and flips to the live APIs with a single configuration flag. The engine performs segmentation, hybrid retrieval, rank fusion, memory-based re-ranking, a restraint policy, and the safety gate.

**The two challenge APIs** sit beneath the engine. Gloo AI Studio provides faith-aligned language understanding and generation; the YouVersion Platform API provides the verified, licensed verse text in the reader's chosen translation.

Tying the surfaces together is **the Resonate Key** — a portable identity token that lets one person share a single memory graph across every AI they use, on any device.

---

## 5. The Two APIs and the Division of Labor

The single most important design idea in Resonate is the *division of labor* between the two APIs, because it is what makes hallucination structurally impossible.

- **Gloo AI Studio** reads a message and segments it into emotional *beats* (themes such as grief, perseverance, or anxiety, each with an emotion label and an intensity score). Later in the pipeline, Gloo also *verifies and selects* the single best verse *reference* from a small vetted shortlist the engine hands it, and finally writes a one-sentence *bridge* connecting the person's words to the verse. **Gloo never supplies verse wording.** It is only ever allowed to return a reference — effectively an index into a fixed list — and short connective prose.

- **The engine** (Resonate's own contribution) does the matching: hybrid retrieval, Reciprocal Rank Fusion, memory re-ranking, the restraint policy, and the deterministic safety gate.

- **The YouVersion Platform API** is the *only* source of verse text. The engine fetches the licensed words *by reference*, and those exact words are the only ones a user ever sees.

Because the model is never in a position to produce Scripture — it can only point at a reference that the engine then resolves through YouVersion — the system cannot hallucinate a verse. This is anti-hallucination *by construction*, not by hoping the model behaves.

On the wire: Gloo uses OAuth2 client-credentials (the engine exchanges a client ID and secret for a one-hour bearer token) and then calls a chat-completions endpoint; for structured tasks it pins a specific model, `gloo-anthropic-claude-haiku-4.5`. YouVersion authenticates with an application key header and fetches passages by USFM reference (for example, `PHP.4.6-PHP.4.7`) in plain-text format, in the licensed translation — the live default is the New International Version.

---

## 6. The Ten-Stage Processing Pipeline

Every message flows through the same ordered stages. Safety is checked *first*, on the raw text, independent of everything else, so a crisis can never be missed or answered with a verse.

- **Stage 0 — Safety gate.** The raw text is checked by a deterministic, phrasing-robust classifier. If it detects crisis language, the pipeline stops immediately and returns a human-help card (and, if the user has opted in, a guardian alert). No verse, no model call.
- **Stage 1 — Segmentation.** Gloo splits the message into emotional beats: themes, an emotion, and an intensity from 0 to 1.
- **Stage 2 — Vocabulary check.** A beat whose themes are entirely outside the engine's known vocabulary abstains rather than forcing a wrong verse. Honest silence beats a confident mismatch.
- **Stage 3 — Hybrid retrieval.** Three independent retrievers rank the verse corpus (described in detail below).
- **Stage 4 — Reciprocal Rank Fusion.** The three retrievers' *ranks* are fused into a single ordering.
- **Stage 5 — Memory re-rank and tone-fit.** The candidates are re-scored using a per-user memory graph (recency, theme-fatigue, narrative arcs) and how well each verse's tone fits the beat's intensity.
- **Stage 6 — Confidence and abstention.** If the top candidate isn't clearly the best, the engine abstains rather than guess.
- **Stage 7 — Verify and select.** Gloo picks the single best reference from the top few candidates — constrained to that shortlist.
- **Stage 8 — Verified fetch.** YouVersion returns the licensed text for that reference.
- **Stage 9 — Bridge.** Gloo writes one sentence connecting the person's words to the verse.
- **Stage 10 — Deliver and remember.** The verse is delivered to whichever surface asked, and the theme is recorded in the user's memory graph.

---

## 7. Core Algorithms

### 7.1 Beat Segmentation
A "beat" is one emotional or thematic unit of a message, carrying a set of themes, an emotion label, and an intensity score. In live mode, Gloo produces beats; in offline or fallback mode, a rule-based lexicon segmenter does the same, so the pipeline never breaks. Intensity is amplified by "gravity cues" — words like *mourning*, *grieving*, *loss*, *funeral* — so that understated grief ("I lost my best friend") is still recognized as a heavy moment and gets a comfort-toned verse rather than a bright one.

### 7.2 Hybrid Retrieval
Three independent retrievers each rank a curated corpus of 141 verse references (references and theme tags only — no verse text is stored in the repository):
- A **TF-IDF dense vector** retriever measuring semantic overlap.
- An **Okapi BM25** sparse keyword retriever.
- A **theme-tag** retriever measuring overlap between the beat's themes and each verse's curated emotion labels.
The conversation's recent context also echoes into the query, so the choice follows the whole conversation rather than a single line.

### 7.3 Reciprocal Rank Fusion (RRF)
The three retrievers are combined not by their raw scores — which would need calibration across very different scales — but by their *ranks*. RRF computes, for each verse, the sum over retrievers of 1 divided by (a constant k plus that verse's rank in that retriever). This is robust precisely because it ignores raw score magnitudes; a verse that ranks near the top across all three retrievers wins. This borrows a proven idea from information retrieval and applies it to emotion-to-Scripture matching.

### 7.4 Scoring and Re-rank
After fusion, each candidate gets a final score that blends normalized RRF relevance, a theme-coverage bonus, a tone-fit term (does a comfort verse's intensity range contain this beat's intensity?), and three memory-based penalties and bonuses. The weights are tunable and were tuned against the evaluation harness.

### 7.5 Confidence and Abstention
Confidence is the top candidate's final score expressed as a fraction of the best achievable score. If confidence is low, or the top two candidates are within a small margin, the engine abstains. Restraint is treated as a feature, not a failure.

---

## 8. The Temporal Memory Graph

Resonate remembers, per user, the themes a person keeps returning to. This memory graph drives three behaviors: **recency** (don't repeat a verse just delivered), **theme-fatigue** (don't hammer the same theme twice in a row), and **narrative arcs** (recognize continuity across whole sessions). When a theme recurs enough, the engine can surface a gentle note — for example, "you've returned to anxiety four times lately" — which is the difference between *being searched* and *being known*. The memory layer is thread-safe and can run against a local JSON store or a Redis backend, automatically falling back to local storage if Redis is unavailable. Only sanitized theme labels and counts are ever stored — never the person's words.

---

## 9. The Safety Architecture

The safety gate is the one part of the system that is *deliberately not* delegated to a language model. Crisis detection is a phrasing-robust regular expression run on the raw text, identical in offline and live modes, and checked *before* any model call. The reasoning is simple: a language model can refuse, drift, or be rate-limited, and a missed crisis is the single failure this product must never have. A deterministic rule that always runs is safer than a smart model that sometimes doesn't. The detector covers direct statements, indirect and passive ideation, method-specific language, common slang and abbreviations, and even a few non-English phrasings. When it fires, the person receives crisis-line resources — not a verse — and, if they have explicitly registered trusted "guardians" and consented, those guardians receive a gentle "please check on them" message that never contains what the person wrote. The guardian system is consent-first, privacy-first, and has a cool-down so a hard night never becomes a flood of alerts.

---

## 10. Anti-Hallucination By Construction

This deserves restating as its own principle, because it is the technical heart of the project. In stages 7 and 8 of the pipeline, Gloo is asked only to *choose a reference from a fixed shortlist* — it returns essentially an index, never text — and YouVersion then supplies the words for that reference. Because the model is never asked to produce Scripture, it is never in a position to invent it. Contrast this with the common failure mode of "verse generator" apps, which ask a model to output Scripture directly and then hope the wording is correct. Resonate makes the correct behavior structurally guaranteed rather than probabilistically likely.

---

## 11. The Gloo Alignment Challenge

One genuinely novel engineering result came from a problem that only appears in live use. When emotional, first-person text is sent to a faith-aligned chat model and the system prompt asks it to "return JSON describing the emotional themes," the model's alignment layer often ignores the instruction and instead returns a warm, *pastoral* answer — it counsels the user rather than classifying the text. This is the model being helpful in the wrong way. Resonate defeats this by (1) framing the input as third-party *data to annotate* — text "not addressed to you" — rather than as a message to respond to, (2) pinning a specific structured model, and (3) demanding a strict JSON response format. When the model treats the text as data to label rather than a person to comfort, it classifies cleanly. A lexicon-based fallback runs if parsing ever fails, so the live pipeline can never break. This is a concrete example of "pushing the tools to do something new" — bending a values-aligned model into a reliable structured extractor.

---

## 12. Ezra — The Conversational Scripture Guide

Ezra is a named, warm, Scripture-rooted companion you can chat with or voice-call. Rather than answering from the model's memory, Ezra grounds *every* reply in real retrieved Scripture: a topic-to-theme map plus the same hybrid retrieval pull the fitting verses, YouVersion supplies the exact wording, and only then does the model speak — leading with the verse and its meaning rather than interrogating the user with clarifying questions. Ezra will never claim to "not have a verse," because the retrieval layer always surfaces real Scripture for a genuine topic. On a voice call, replies are capped to a few short spoken sentences, transcription errors are reasoned around, and three synthesized "chapel" voices (produced locally with a neural text-to-speech model) can read the verse aloud.

---

## 13. The Delivery Surfaces

- **ChatGPT browser extension (flagship):** injects a small, dismissible parchment verse panel beside the chat, with optional voice, a "your story" reflection, and links to story reels. It reads only the user's own message, processes locally, and stores nothing. It fails invisibly — if the engine is offline, it simply does nothing and never breaks the host chat.
- **MCP server:** exposes Scripture as a native capability to any assistant that speaks the Model Context Protocol, over local stdio or hosted over HTTP so that a single URL is the entire install. Four tools are exposed: resonate_verse, generate_story, reel_groups, and fetch_passage. The engine's guarantees (safety-first, verified text, story labels, shared memory) all hold server-side no matter what the model asks.
- **Reels for you:** a Spotify-style shelf of verse-matched story films, using real YouVersion partner video posters.
- **VS Code and Discord:** Scripture in the margins where builders think, and Scripture as conversation rather than broadcast.

---

## 14. The Resonate Key — One Person, One Memory, Any AI

A person is one individual, not one account per chatbot. The Resonate Key is a short portable identity token that a user carries in a hosted URL, a local flag, or a browsing prompt. The same key used in ChatGPT, Claude, and Cursor — on any device — reaches the *same* temporal memory graph, so the "you've returned to this lately" continuity follows the person, not the bot. The extension, the MCP tools, and the web pages all deepen that one graph when they share the key.

---

## 15. Multi-User Architecture and Scale

The engine is designed to serve many users concurrently. The per-user memory is thread-safe (guarded reads and writes under a shared server), partitioned by user identity, and backed by either local storage or Redis with automatic fallback. Sliding-window rate limiting protects every endpoint per user, while crisis input is always exempt so that help can never be rate-limited away. Fetched YouVersion passages are cached to disk so any given verse is fetched at most once, which keeps the conversational guide responsive and conserves API quota. Conversations are stateless on the server — history rides with each request — so the engine scales horizontally behind a shared memory store.

---

## 16. Technology Stack and Engineering Practices

The core engine is pure Python standard library, which keeps it dependency-light and fully runnable offline. Every external call sits behind a *mock/live adapter*: in mock mode the system uses local embeddings, public-domain sample text, and local memory, so it runs anywhere with no keys; in live mode it flips to the real Gloo and YouVersion APIs with one configuration change. An "auto" mode uses each provider live when its keys are present and mock otherwise, so a demo never half-breaks. This adapter pattern also makes the test suite hermetic and deterministic.

---

## 17. Verification and Evaluation

Resonate ships with a **103-case unit test suite** and a **42-scenario evaluation harness**, and the evaluation thresholds are themselves enforced by a unit test so that quality can never silently regress. On the offline evaluation set the engine achieves 100% theme recall, 96.2% verse hit@1, 100% hit@3, 100% safety recall across 14 distinct crisis phrasings (including indirect, method-specific, and slang variants), and a 0% false-positive rate on the safety gate. Beyond the offline suite, the system is verified *live*: the hosted deployment reports both providers as live, a grief query returns real modern-translation wording sourced from YouVersion (not a local sample), and crisis input returns a safety hold with no verse. This combination — a reproducible offline harness plus live verification against both real APIs — is what lets a reviewer trust that the demo is genuinely functional and not faked.

---

## 18. Reproducibility and Deployment

The whole system can be reproduced offline with no keys and no installs: clone the repository, run the end-to-end demo, run the restraint-policy demo, run the test suite, run the evaluation harness, start the local engine server, and open the MCP smoke client — all on the standard library alone. Going live is a matter of pasting the Gloo client credentials and the YouVersion application key into an environment file and running a preflight check that validates the entire chain (Gloo OAuth, a completion, the YouVersion catalog, a passage fetch, and an end-to-end engine call). Free public hosting is provided via Render. The project is MIT-licensed; no verse text is redistributed in the repository — it is always fetched at runtime from YouVersion under its own license terms.

---

## 19. Why It Matters

Resonate treats the arrival of Scripture into someone's day as something that must be *earned*: it must fit the moment, it must be verified, it must know when to stay silent, and it must protect a person in crisis before it does anything else. The technical work — hybrid retrieval fused by RRF, a temporal memory graph, a deterministic safety gate, anti-hallucination by construction, and a prompt technique that bends a pastoral model into a reliable extractor — all serves that single human goal: to make Scripture present where life actually happens, on the user's terms, and never intruding.

*Live demo: https://resonate-hg6j.onrender.com · Source: https://github.com/krizz711/resonate*
