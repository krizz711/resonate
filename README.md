# Resonate — Scripture, where you already are

![Resonate cover](docs/cover.svg)

Billions now type their most honest words — grief, burnout, doubt — into **AI chatbots**, not a
Bible app. Scripture has never been present there. **Resonate** is the bridge: it weaves
*verified* Scripture into the conversations people already have — quietly, safely, and only when
it truly fits.

Built for the Kaggle hackathon **Scripture in New Frontiers** (frontier: *AI & digital
assistants*). Uses the **YouVersion Platform API** + **Gloo AI Studio API**. Submissions close
**July 31, 2026** — one submission per team. MIT-licensed (OSI-approved, per the winning
requirements).

> **Not another Bible app.** You never open anything. The verse appears inside the tool you're
> already in — as a small, dismissible parchment panel — processed locally, storing nothing.

## The surfaces — *you choose where Scripture meets you*
One engine, many native delivery surfaces (this is the architecture, not a slogan):

| Surface | What it is | Where |
|---|---|---|
| **ChatGPT extension** *(flagship)* | a quiet verse beside your AI chat — with voices, "your story", reels | [`integrations/chatgpt-extension`](integrations/chatgpt-extension) |
| **MCP server** | Scripture as a native capability for ANY assistant (Claude, ChatGPT, Gemini…) — stdio locally, or **hosted over HTTP at `/mcp`** so a URL is the whole install | [`integrations/mcp`](integrations/mcp) |
| **VS Code companion** | Scripture in the margins where builders think | [`integrations/vscode`](integrations/vscode) |
| **Discord bot** | Scripture as conversation, not broadcast | [`integrations/discord`](integrations/discord) |

**One brain across every AI — the Resonate Key.** A person is one individual, not one
account per chatbot. Generate a key on `/connect.html` (e.g. `RSN-7K2P`); carry it in the
hosted URL (`…/mcp?key=RSN-7K2P`), the local `--key` flag, or the browsing prompt. Same key
in ChatGPT, Claude, Cursor, on any device → the **same** temporal memory graph (recurring
themes, "you've returned to this lately"). The extension, the MCP tools, and the web pages all
write to that one graph when they share the key.

## How it works — a context engine between the two APIs
- **Gloo AI Studio** reads the message → emotional *beats* and writes the one-line *bridge*.
  *Never recites Scripture.*
- **The engine** matches each beat with **hybrid retrieval** (TF-IDF + BM25 + theme tags fused via
  **Reciprocal Rank Fusion**), re-ranks by tone-fit + a per-user **temporal memory graph**, and a
  **Delivery Policy** decides whether to speak at all. A **phrasing-robust safety gate** on the raw
  text routes any crisis to a human-help card — never a verse (safety is deterministic, not left
  to a model).
- **YouVersion Platform API** returns the verified, licensed verse text. The model proposes a
  reference from a vetted shortlist; YouVersion confirms the words — nothing is hallucinated.

Full design: [ENGINE-DESIGN.md](ENGINE-DESIGN.md).

## What makes it native, not a pop-up
1. **Restraint.** Silent on ordinary messages; speaks only on a real, high-confidence beat;
   rate-limited; learns from dismissals. (`resonate/policy.py`)
2. **Safety first.** Crisis text is caught on the raw input and routed to a **human-help card —
   never a verse** (100% recall on the eval set).
3. **Memory over time.** It notices recurring themes — *"you've returned to this 4× lately"* —
   personalization across conversations, not one sentence.
4. **Privacy.** Reads only the user's own message, locally; stores nothing; opt-in per site. An
   optional warm voice can read the verse aloud.

## Reproduce it (offline — no keys, no installs)
Requirements: **Python 3.11+** and a Chromium browser. The engine core runs on the Python
standard library alone (mock providers + local memory) — clone and run:
```bash
git clone https://github.com/krizz711/resonate && cd resonate
python scripts/demo.py                         # 1. end-to-end engine demo (creator transcript)
python scripts/policy_demo.py                  # 2. the Delivery Policy staying quiet at the right times
python -m unittest discover -s tests           # 3. 98 tests (incl. the eval regression guard)
python eval/run_eval.py                        # 4. 42-scenario evaluation harness
python scripts/serve.py                        # 5. local engine  ->  http://127.0.0.1:8765
python integrations/mcp/smoke_client.py        # 6. MCP surface: real stdio session, all 4 tools
```
With the server running, open **http://127.0.0.1:8765** — the site's closing section (and
**/connect.html**) gives the copy-paste MCP block that adds Resonate to Claude, ChatGPT, Gemini
or Cursor. For the flagship surface, load `integrations/chatgpt-extension` at
`chrome://extensions` → Developer mode → Load unpacked, and chat on chatgpt.com — verse panel,
wax-seal fold, voices, reels. The VS Code surface: open `integrations/vscode`, press F5.

**Optional voices** (Kokoro TTS): install [Kokoro-82M](https://github.com/hexgrad/kokoro) in any
venv (`pip install kokoro soundfile`), set `RESONATE_KOKORO_PY` to that venv's python, have
`ffmpeg` on PATH — the panel's Listen button then uses Bella/Isabella/George; without it, the
browser voice is used automatically.

## Go live (competition keys, from 2026-07-06)
```bash
cp .env.example .env         # paste GLOO_CLIENT_ID/SECRET + YOUVERSION_APP_KEY
pip install httpx
python scripts/live_check.py # validates: Gloo OAuth -> completion -> YouVersion catalog
                             # (resolves your RESONATE_BIBLE_ID) -> passage -> engine end-to-end
```
Then set `RESONATE_MODE=live` in `.env` and restart `scripts/serve.py`. Accept your Bible's
license agreement under **Licensing** on platform.youversion.com first, or passage calls 4xx.

## Free cloud deploy
Render free web services can host the mock demo publicly. This repo includes `render.yaml`;
push to GitHub, create a Render Blueprint, and use the generated URL for the Kaggle project link.
See [docs/CLOUD-DEPLOY.md](docs/CLOUD-DEPLOY.md).

## Verification — *proof it works*
Current metrics (enforced as a regression guard in the test suite): **theme recall 100% ·
verse hit@1 96% · hit@3 100% · safety recall 100% · false-positive 0%**.

## Submission assets
- 🎬 Video script — [docs/VIDEO-SCRIPT.md](docs/VIDEO-SCRIPT.md)
- 📄 Writeup (≤500 words) — [docs/WRITEUP.md](docs/WRITEUP.md)
- 📓 Public notebook — [notebook/resonate_demo.ipynb](notebook/resonate_demo.ipynb)
- 🖼 Cover image — [docs/cover.svg](docs/cover.svg)
- 🧭 Competitiveness review — [docs/COMPETITIVENESS.md](docs/COMPETITIVENESS.md)
- Cloud deploy guide — [docs/CLOUD-DEPLOY.md](docs/CLOUD-DEPLOY.md)

## Layout
```
resonate/        engine package — config, models, embeddings, verses, retrieval,
                 memory, policy, engine (orchestrator), responder, providers/(gloo, youversion)
integrations/    chatgpt-extension/ · mcp/ · vscode/ · discord/   (delivery surfaces)
data/            verses.json (141 refs+tags, no text) · sample_texts.json (KJV demo text)
scripts/         demo.py · policy_demo.py · serve.py (local engine server)
web/             engine-served pages: Ezra (guide) · reels · connect · guardians · panel preview
eval/            dataset.json + run_eval.py (metrics)
tests/           test_resonate.py (98 cases incl. the eval guard)
docs/            video script · writeup · cover · competitiveness review
```

## Status
Engine, all surfaces, restraint, safety, memory, voices, reels, tests + eval — **built and green**
(98 tests; runs anywhere offline in mock mode). **Live now:** the hosted deployment runs against
both challenge APIs — Gloo OAuth2 client-credentials → `/ai/v2/chat/completions`, and YouVersion
`X-YVP-App-Key` → `/v1/bibles/{id}/passages/{USFM}?format=text` — verified end-to-end by
`python scripts/live_check.py` and `python scripts/e2e_smoke.py <url>`. `RESONATE_MODE=auto` uses
each provider live when its keys are present and mock otherwise, so the demo never half-breaks.
