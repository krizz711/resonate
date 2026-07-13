# Free Cloud Deploy

This project can run online for free in mock mode first. That gives judges and teammates a public demo link while you keep editing the product.

Recommended host: Render Free Web Service.

Why Render:

- It supports free Python web services.
- It can deploy straight from GitHub.
- The existing `scripts/serve.py` server works without FastAPI, Flask, or Node.
- The free instance is enough for a hackathon demo.

Important free-tier limits:

- The service may sleep after about 15 minutes without traffic.
- First request after sleep can take around a minute.
- Local filesystem changes are not permanent after restart/redeploy.
- Use mock mode for the public demo unless you are ready to add live API keys.

## What Is Cloud-Ready Now

- Landing page: `/` (its closing section carries the copy-paste MCP config)
- Connect guide (per-app MCP setup): `/connect.html`
- Ezra, the Scripture Guide: `/guide.html`
- Reels for you: `/reels.html`
- Guardian registration: `/guardians.html`
- Panel preview: `/panel-preview.html`
- Health check: `/health`
- Resonate API: `POST /resonate`
- Story API: `POST /story`

MCP note: the browser UI shows visitors HOW to connect (landing footer + `/connect.html`), but MCP itself is a separate stdio integration run by AI clients such as Claude Desktop, Claude Code, or Cursor on the visitor's own machine.

## Deploy On Render

1. Push this repo to GitHub.

2. Go to Render and create a new Blueprint from the repo.

3. Render should detect `render.yaml`.

4. Confirm these settings:

   - Service type: Web Service
   - Environment: Python
   - Plan: Free
   - Build command: `pip install -r requirements.txt && cd site && npm ci && npm run build`
     (the site is BUILT ON RENDER — `site/dist` is deliberately not in git, so a
     pip-only build command leaves the landing page 404ing with a
     "site/dist not built" hint)
   - Start command: `python scripts/serve.py`
   - Health check path: `/health`

5. Deploy.

6. Open the public URL Render gives you.

Useful URLs after deploy:

- `https://YOUR-SERVICE.onrender.com/`
- `https://YOUR-SERVICE.onrender.com/connect.html`
- `https://YOUR-SERVICE.onrender.com/guide.html`
- `https://YOUR-SERVICE.onrender.com/reels.html`
- `https://YOUR-SERVICE.onrender.com/health`

## Add Live API Keys Later

Keep the first deploy in mock mode. When you are ready to use live Gloo and YouVersion APIs:

1. In Render, open the service settings.

2. Add environment variables:

   - `RESONATE_MODE=live`
   - `GLOO_CLIENT_ID=...`
   - `GLOO_CLIENT_SECRET=...`
   - `YOUVERSION_APP_KEY=...`
   - `RESONATE_BIBLE_ID=...`
   - `RESONATE_TRANSLATION=KJV` or your chosen translation

3. Accept the Bible license agreement in the YouVersion Platform dashboard.

4. Redeploy.

5. Check `/health`.

Before switching public demo traffic to live mode, run locally:

```bash
python scripts/live_check.py
```

## Submission Link Strategy

For Kaggle, use the deployed URL as the public project link.

Recommended demo path for judges:

1. Open `/` and scroll — the story, the metrics, and the copy-paste MCP block.
2. Open `/guide.html` and ask Ezra: `I feel like I am failing everyone and I cannot keep up.`
3. Ask Ezra `What does Psalm 23:1-3 say?` — verbatim, licensed wording via YouVersion.
4. Open `/reels.html`, share a moment, watch the shelves re-rank.
5. Connect a real assistant via `/connect.html` and say “I'm exhausted and losing hope.”

## Troubleshooting

If the app does not start:

- Check Render logs.
- Confirm the start command is `python scripts/serve.py`.
- Confirm `RESONATE_HOST=0.0.0.0`.
- Confirm Render provides `PORT`; the server now reads it automatically.

If the app is slow:

- It probably slept on the free tier. Refresh after one minute.

If story or voice buttons fall back:

- Voice synthesis is optional. Browser speech fallback is expected if Kokoro is not installed on the cloud service.

If live passages fail:

- Check `YOUVERSION_APP_KEY`.
- Check `RESONATE_BIBLE_ID`.
- Accept the Bible license in the YouVersion dashboard.
- Run `python scripts/live_check.py` locally and fix its hints.
