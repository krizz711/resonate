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

- Landing page: `/`
- Mock chat demo: `/mock-chat.html`
- Panel preview: `/panel-preview.html`
- Engine playground: `/playground.html`
- Health check: `/health`
- Resonate API: `POST /resonate`
- Story API: `POST /story`

MCP note: visitors do not access MCP through the browser UI. MCP is a separate stdio integration for AI clients such as Claude Desktop, Claude Code, or ChatGPT developer-mode clients. The cloud UI exposes the web demo and HTTP endpoints.

## Deploy On Render

1. Push this repo to GitHub.

2. Go to Render and create a new Blueprint from the repo.

3. Render should detect `render.yaml`.

4. Confirm these settings:

   - Service type: Web Service
   - Environment: Python
   - Plan: Free
   - Build command: `pip install -r requirements.txt`
   - Start command: `python scripts/serve.py`
   - Health check path: `/health`

5. Deploy.

6. Open the public URL Render gives you.

Useful URLs after deploy:

- `https://YOUR-SERVICE.onrender.com/`
- `https://YOUR-SERVICE.onrender.com/mock-chat.html`
- `https://YOUR-SERVICE.onrender.com/playground.html`
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

1. Open `/mock-chat.html`.
2. Type: `I feel like I am failing everyone and I cannot keep up.`
3. Show the verse panel.
4. Type a neutral question and show Resonate staying silent.
5. Type a crisis-style test message only in a controlled demo, then show the help card.
6. Open `/playground.html` to show the engine response.

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
