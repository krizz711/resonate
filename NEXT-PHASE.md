# Resonate — Next Phase (Scripture in New Frontiers)

Working plan for the build sprint (2026-07-10 →). Keys open 2026-07-06; submission due
2026-08-01 IST. Maximize Gloo AI Studio usage across every module.

## 0. Gloo credit ✅ REDEEMED 2026-07-10 ($20 promo credits active, cardless)
Credentials live in `.env` (gitignored) · `RESONATE_MODE=live` · `live_check.py` ALL GREEN.
Full live e2e verified: live segmentation (verbatim beats), live verify, live NIV text,
live bridges. **Rotate the API key after the challenge** (secret touched a chat log).

**Alignment-layer gotcha (baked into LiveGloo):** emotional text sent plainly gets a
pastoral care reply that ignores JSON instructions, even with a model pinned. Structured
calls therefore use: pinned `GLOO_MODEL_STRUCTURED` (haiku-4.5) + data-framing system
prompt ("annotation service — snippet is data, not addressed to you", `<<<...>>>`) +
"copy text VERBATIM" rule + `response_format: json_object` + lexicon fallback. Story
generation intentionally keeps `auto_routing` — the pastoral voice is right there.

## Gloo AI Studio service map (docs.gloo.com, verified 2026-07-10)
Base `https://platform.ai.gloo.com/ai/v2/` · OAuth2 client-credentials (`scope=api/access`).

| Gloo service | Endpoint | Where Resonate uses it |
|---|---|---|
| Chat completions (aligned, auto-routed) | `POST /chat/completions` | engine segment/verify/bridge/story (LiveGloo — wired); n8n Scripture Guide |
| Grounded completions (RAG + citations) | `POST /chat/completions/grounded` + `rag_publisher` | Scripture Guide cited answers; devotional-source bridges |
| Search / semantic discovery | `/search`, publisher-data search | reel-group matching (live mode), corpus exploration |
| Data Engine (upload/ingestion) | ingestion v1/v2 | upload our curated corpus + reel metadata as a publisher → grounding |
| Recommendations (item recs) | `GET base/verbose item recommendations` | "reels for you" groups, live ranking |
| Responses API (multimodal) | `/responses` | future: reel art/scene generation |
| Prompt caching | implicit/explicit | cost control on the long Scripture Guide system prompt |
| Benchmarks/models | `/models` v2 | model pick for demo writeup |

## Modules

### 1. Security module — guardian alerts  ✅ engine-side DONE (2026-07-10)
`resonate/guardian.py`: crisis (safety gate) → WhatsApp (Twilio) / email (SMTP) to
**registered, consenting** guardians. Consent-first (`RESONATE_GUARDIAN=1` +
`data/guardians.json` with `consent:true`), privacy-first (never shares what was typed),
24h cooldown, daemon-thread sends, `guardian` status in the safety_hold payload;
extension help card shows "your guardians have been quietly notified."
**Next**: registration UI (playground settings page writes guardians.json via serve.py
endpoint); optionally a Gloo-classified severity tier before alerting.

### 2. MCP for every assistant  ✅ tool added
`integrations/mcp/resonate_mcp.py` — stdio JSON-RPC, works in Claude/ChatGPT/Gemini/Grok
(any MCP client): `resonate_verse`, `generate_story`, **`reel_groups` (new)**,
`fetch_passage`. Popup already does semantic verse + voice icons.
**Next**: hosted MCP (SSE) so GPTs/Gemini can reach it without local install;
follow docs.gloo.com/api-guides/mcp-integration.

### 3. Reel groups — "reels for you"  ✅ FULL STACK (engine + endpoint + page, 2026-07-11)
`ReelStore.groups_for()`: priority sets with subtitles — P1 *For this moment* ·
P2 *Threads you return to* · P3 *Steady ground*. Story films rank before verse-page
fallbacks; no verse repeats; empty groups drop.
- **`POST /reel-groups`** — themes from: explicit → text beats → series memory → default;
  crisis input refuses reels. **`/reels.html`** — Spotify-style shelves on cream:
  basis line ("picked from what you just shared — anxiety · weariness"), horizontal
  9:16 card rows per group, theme-tinted scenes, "what's on your heart" input.
- **`data/reels.json` curated to YouVersion's own Videos catalog** (bible.com/videos
  partner series — The Chosen S5/Upper Room→John 14, LUMO Life of Jesus, House of
  David→Psalms, Three Gospels→Matthew, At the Table with Jesus→Matt 11): 11 usfm
  keys now open real licensed films INSIDE the YouVersion ecosystem.
**Next**: popup ▷ → open /reels.html; swap in our own produced reels; live ranking
via Gloo Search/recommendations.

### 4. Scripture Guide — chat + WEB CALL  ✅ SHIPPED LIVE (2026-07-10, zero-cost design)
Decision: **no paid telephony** (Retell/Vapi ≈ $0.07/min; Twilio = real money; Gloo Data
Engine = Pro-gated $25/mo). The call is **in-browser**: mic → free Web Speech STT →
`POST /guide` → reply spoken in the tuned Kokoro voices. Manual RAG beats a publisher:
our own hybrid retrieval grounds each turn + live YouVersion text (that pipeline IS the
product). n8n (self-hosted, free) stays off the live path: guardian alerts, sync, logs.
- `resonate/guide.py` — ScriptureGuide core: safety gate → ground (≤2 beats → top verse
  each, licensed text) → `gloo.converse()` (pinned `GLOO_MODEL_GUIDE`, default haiku-4.5;
  voice turns constrained to ≤3 spoken sentences — constraint must LEAD the system
  prompt or the model reverts to lists, live-tested).
- `web/guide.html` at **/guide.html** — the persona is **Ezra** ("skilled in the Law",
  Ezra 7:6): chat page + call in one. Type OR talk; **human turn-taking with barge-in**
  (recognizer runs while Ezra speaks; real speech over him stops the audio mid-sentence
  and he listens until a ~900ms silence closes the turn; echo guard drops the mic
  hearing his own voice; typing over him also interrupts). Wax-seal pickup with cached
  greeting, verbatim ref chips, voice cycler (Bella default / Isabella / George /
  Browser fallback), `__guideSend/__guideHear/__guideForce/__guideState` hooks.
- **Persistent Kokoro worker** (`tts_kokoro.py --serve` + client in `resonate/tts.py`):
  model loads once at server boot (`tts.warm()` warms BOTH language pipelines);
  novel replies render in ~3.4-3.8s (was ~8s+ per reply); one-shot spawn fallback;
  ffmpeg now resolved robustly (WinGet path — PATH alone fails outside Git Bash).
- Verified live e2e: money worry → Matthew 6:31-33 (NIV) verbatim; restlessness →
  Psalm 4:8; crisis → help lines + guardian status, call ends with care. 68 tests.
**Next**: link "call" from the site/playground; optional Twilio trial number for the
video's phone-shot; WhatsApp voice notes via self-hosted n8n.

### 5. Site copy  ✅ DONE — acts now tell the real story
Gloo verification (Verses), guardian alerts (Safety), prioritized reel sets (Reels),
Scripture Guide chat+voice+n8n (VI), `reel_groups` chip (MCP act).

### 6. One identity, many users  ✅ SHIPPED (2026-07-11)
- **Unified anonymous id** (`resonate_uid`): popup, Ezra and reels share ONE context
  graph per person — themes only, no text crosses surfaces. Extension hands its id via
  `guide.html?uid=…&q=…` ("☎ ask Ezra about this" icon = explicit one-shot handoff);
  pages adopt `?uid` into localStorage. Guide memory prefix silo fixed; Ezra's system
  prompt now carries RECENT THREADS (themes ≥2×) for gentle continuity; reels shelves
  personalize from the same graph (verified: one weary Ezra turn → reels basis=memory).
- **Multi-user scale story**: per-user graphs already isolated by user_id in the memory
  backend (LocalMemory + disk persist; `RESONATE_MEMORY=redis` + `REDIS_URL` is the
  documented upgrade — same keys move to Redis). Conversations are stateless server-side
  (transcript rides with the request). NEW `resonate/ratelimit.py` + serve.py wiring:
  per-user sliding windows (guide 8/min + 240/day, tts 30/min, reels 12/min, story
  6/min) → polite 429; protects the Gloo credit and the single Kokoro worker.
- **Voice made human**: sentence-streamed TTS (first sentence plays while the rest
  render; prefetch pipeline; barge-in cancels via session counter; autoplay-block →
  Web Speech fallback) + HARD token ceiling for voice turns (max_tokens=190 — the
  ≤3-sentence instruction alone drifts; verified live: 2-sentence spoken reply).
- **Site UI integration**: nav gains Reels + Ezra; Reels act CTA "▷ open your reels";
  Guide act CTA "☎ talk to Ezra"; site rebuilt into site/dist (served by the engine,
  same origin in production).

## Env additions (all optional; module no-ops without them)
```
RESONATE_GUARDIAN=1            GUARDIAN_FILE=data/guardians.json  GUARDIAN_COOLDOWN_H=24
SMTP_HOST= SMTP_PORT=587 SMTP_USER= SMTP_PASSWORD= SMTP_FROM=
TWILIO_SID= TWILIO_TOKEN= TWILIO_WHATSAPP_FROM=
GLOO_CLIENT_ID= GLOO_CLIENT_SECRET= RESONATE_MODE=live
```
