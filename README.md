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
| **ChatGPT extension** *(flagship)* | a quiet verse beside your AI chat | [`integrations/chatgpt-extension`](integrations/chatgpt-extension) |
| **VS Code companion** | Scripture in the margins where builders think | [`integrations/vscode`](integrations/vscode) |
| **Discord bot** | Scripture as conversation, not broadcast | [`integrations/discord`](integrations/discord) |

## How it works — a context engine between the two APIs
- **Gloo AI Studio** reads the message → emotional *beats*, writes the one-line *bridge*, runs
  safety. *Never recites Scripture.*
- **The engine** matches each beat with **hybrid retrieval** (dense + BM25 + theme tags fused via
  **Reciprocal Rank Fusion**), re-ranks by tone-fit + a per-user **temporal memory graph**, and a
  **Delivery Policy** decides whether to speak at all.
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
python -m unittest discover -s tests           # 3. 49 tests (incl. the eval regression guard)
python eval/run_eval.py                        # 4. 32-scenario evaluation harness
python scripts/serve.py                        # 5. local engine  ->  http://127.0.0.1:8765
```
With the server running, either open **http://127.0.0.1:8765/mock-chat.html** (a faithful
ChatGPT stand-in running the real extension script — verse panel, wax-seal fold, voices, reels),
or load `integrations/chatgpt-extension` at `chrome://extensions` → Developer mode → Load
unpacked, and chat on chatgpt.com. The VS Code surface: open `integrations/vscode`, press F5.

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

## Verification — *proof it works*
Current metrics (enforced as a regression guard in the test suite): **theme recall 100% ·
verse hit@1 96% · hit@3 100% · safety recall 100% · false-positive 0%**.

## Submission assets
- 🎬 Video script — [docs/VIDEO-SCRIPT.md](docs/VIDEO-SCRIPT.md)
- 📄 Writeup (≤500 words) — [docs/WRITEUP.md](docs/WRITEUP.md)
- 📓 Public notebook — [notebook/resonate_demo.ipynb](notebook/resonate_demo.ipynb)
- 🖼 Cover image — [docs/cover.svg](docs/cover.svg)
- 🧭 Competitiveness review — [docs/COMPETITIVENESS.md](docs/COMPETITIVENESS.md)

## Layout
```
resonate/        engine package — config, models, embeddings, verses, retrieval,
                 memory, policy, engine (orchestrator), responder, providers/(gloo, youversion)
integrations/    chatgpt-extension/ · vscode/ · discord/   (delivery surfaces)
data/            verses.json (131 refs+tags, no text) · sample_texts.json (KJV demo text)
scripts/         demo.py · policy_demo.py · serve.py (local engine server)
web/             control-panel playground served by the engine
eval/            dataset.json + run_eval.py (metrics)
tests/           test_resonate.py (49 cases incl. the eval guard)
docs/            video script · writeup · cover · competitiveness review
```

## Status
Engine, all three surfaces, restraint, safety, memory, voices, reels, tests + eval — **built and
green in mock mode** (runs anywhere offline). The live Gloo + YouVersion providers are
**pre-wired to the documented APIs** (Gloo OAuth2 client-credentials → `/ai/v2/chat/completions`
with auto-routing; YouVersion `X-YVP-App-Key` → `/v1/bibles/{id}/passages/{USFM}?format=text`)
— when challenge keys open (**2026-07-06**), `python scripts/live_check.py` validates the whole
chain and `RESONATE_MODE=live` flips it on.
