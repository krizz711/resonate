# Scripture Guide — the n8n bot (chat + voice)

**Scripture Guide** is Resonate's conversational surface: an assistant that knows the
Scriptures deeply and can discuss them with people — in a chat box, or by voice message /
phone call — powered end-to-end by **Gloo AI Studio** (values-aligned chat with
`auto_routing`, grounded RAG later via `/chat/completions/grounded`).

## What's here

`scripture-guide.workflow.json` — an importable n8n skeleton:

```
Webhook (POST /scripture-guide)  →  Build Gloo Messages (Code)
   →  Gloo Chat completions (HTTP, OAuth2 client-credentials)  →  Respond
```

## Setup

1. **Import** the workflow (n8n → Workflows → Import from file).
2. **Credential**: create an *OAuth2 API* credential —
   - Grant type: `Client Credentials`
   - Access-token URL: `https://platform.ai.gloo.com/oauth2/token`
   - Client ID / Secret: from [Studio → Settings → API credentials](https://studio.ai.gloo.com/settings/api-keys)
   - Scope: `api/access`
   Attach it to the **Gloo Chat** node.
3. **Activate** and POST `{"text": "...", "history": ["..."]}` to the webhook URL.

## Production hardening (next passes)

- **Safety first**: call the Resonate engine (`POST /resonate`) *before* Gloo chat; on
  `safety_hold`, return the help card (and let the engine's guardian module alert
  registered guardians) — never a chat answer.
- **Grounding**: swap the chat node's URL to `/ai/v2/chat/completions/grounded` with
  `rag_publisher` set to our uploaded corpus publisher for cited answers.
- **Voice in**: WhatsApp/Telegram trigger → download voice note → transcribe →
  same chain. **Voice out**: pipe the reply through the engine's `/tts` (Kokoro,
  godly preset) and send the audio file back.
- **Phone calls**: Twilio Voice webhook → n8n; stream TTS reply as the call audio
  (the "call Scripture Guide" pitch from the site).
- **Memory**: pass a stable `user_id` through to the engine so series memory
  ("you've returned to this") spans the bot too.
