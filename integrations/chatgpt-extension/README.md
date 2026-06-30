# Resonate — ChatGPT connector (flagship)

Scripture, in the AI-powered world you already live in. Resonate sits quietly in the corner of
your ChatGPT window. It **reads only your message text, processes it locally, stores nothing**,
and **only speaks when it hears a story that echoes a verse** — appearing as a small, dismissible
side panel. When it detects a crisis, it **stays silent on Scripture and points to help instead.**

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
local server, which runs the matching engine + safety gate + Delivery Policy.

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
