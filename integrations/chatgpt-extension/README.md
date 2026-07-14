# Resonate — ChatGPT connector (flagship)

Scripture, in the AI-powered world you already live in. Resonate sits quietly in the corner of
your ChatGPT window. It **reads only your message text, processes it locally, stores nothing**,
and **only speaks when it hears a story that echoes a verse** — appearing as a small, dismissible
side panel. When it detects a crisis, it **stays silent on Scripture and points to help instead.**

## Panel v2 — what it does now
- **Slips in from the right** (0.5 s, eased; honors `prefers-reduced-motion`), compact 340 px,
  floating above the composer so it never covers the conversation or the input.
- **Folds itself away**: after ~14 s without your attention the card folds into a small **wax
  seal** in the corner — the verse waits without taking your space. Click the seal to unfold.
- **A voice from an old chapel**: ▸ Listen speaks the verse with a Kokoro voice served by the
  local engine — cycle **Bella / Isabella / George** (each tuned: unhurried tempo, lowered
  pitch, warm bass, a quiet chapel reverb). `auto: on` reads every verse as it arrives
  ("play by default"). If the voice engine is offline it falls back to the browser's voice.
- **Watch the story**: each verse carries a reel link — a curated story-reel when one exists
  (`data/reels.json`), otherwise the verse's own YouVersion page.
- **Conversation-aware**: the last few messages travel with the newest one, so a "money worry"
  conversation gets *"my God shall supply all your need"* (Philippians 4:19), not a generic
  anxiety verse. History sharpens WHICH verse — it never decides WHETHER to speak.

## How it works
```
ChatGPT page ──[data-message-author-role="user"]──► content.js (MutationObserver)
        │                                                │ message text
        │                                                ▼
        │                                          background.js  ──fetch──►  local engine
        │                                                                     (scripts/serve.py)
        ▼                                                                          │
 side panel ◄── verse / help card ◄── Delivery Policy decides surface/silence ◄────┘
```
The engine never runs in the page (privacy + the page's CSP). The background worker calls the
engine — a **local server** (`scripts/serve.py`) when one is running, otherwise the **hosted
Resonate server** — which runs the matching engine + safety gate + Delivery Policy.

## Run it
1. **Start the engine** (from the repo root):
   ```bash
   python scripts/serve.py
   ```
2. **Load the extension:** open `chrome://extensions` → enable **Developer mode** →
   **Load unpacked** → select this folder (`integrations/chatgpt-extension`).
3. Open **https://chatgpt.com**, send a message like *"I feel like I'm failing everyone."*
   A quiet verse panel appears bottom-right. Try *"what's the capital of France?"* → silence.
   Try a crisis phrase → a gentle help card, never a verse.

**No local engine? (end users / no-Plus ChatGPT)** Skip step 1. When no local server answers on
`127.0.0.1:8765`, the worker automatically falls back to the hosted Resonate server, so the
extension works with only step 2 (Load unpacked). The one trade-off: hosted runs in mock mode, so
voices fall back to the browser's Web Speech instead of the local Kokoro chapel voices. The connect
page's ChatGPT tab offers this as a one-click `chatgpt-extension.zip` download.

**No ChatGPT handy?** The panel's parchment skin (verse + crisis variants) is previewable at
`http://127.0.0.1:8765/panel-preview.html`, and any MCP assistant gets the same engine via
`/connect.html`. (A throwaway chatgpt.com stand-in for filming lives in git history as
`web/mock-chat.html`, removed from the public UI on 2026-07-13.)

**Tune the voices:** `python scripts/voice_lab.py` renders a matrix of speed/pitch variants per
voice into `data/voice-lab/index.html` — pick the godliest by ear, adjust `resonate/tts.py`.

## Privacy
- Only your **own message text** is read (via the standard message selector), only on chatgpt.com.
- It's sent **to a server on your own machine** (`127.0.0.1`), never to a third party.
- **Nothing is stored**; the session id is random and in-memory.
- If the engine isn't running or the selector changes, the extension simply does nothing — it
  never alters or breaks the chat.

## Architecture note
This is one **delivery surface** of the Resonate engine (see `../../ENGINE-DESIGN.md`). The same
engine + Delivery Policy power the VS Code connector and could power Discord, wearables, or an
MCP tool — you choose where Scripture meets you.
