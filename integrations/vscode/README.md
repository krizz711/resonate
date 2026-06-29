# Resonate — VS Code connector

Scripture in the margins where builders think. A quiet verse for the moment you're in, surfaced
inside your editor — no separate app, no screen-scraping. It reads only the signals VS Code
already exposes (time at work, unresolved errors, the code you've selected), turns them into a
short context, and asks the Resonate engine for the right verse.

## Run it (no build step — it's plain JavaScript)
1. **Start the engine** (from the repo root):
   ```bash
   python scripts/serve.py
   ```
   Leave it running (http://127.0.0.1:8765).
2. **Open this folder** (`integrations/vscode`) in VS Code.
3. Press **F5** ("Run Resonate Extension"). A new *Extension Development Host* window opens.
4. In that window, look at the **bottom-right status bar**: `✝ Resonate`.
   - Click it (or run **"Resonate: A verse for this moment"** from the Command Palette) to surface a verse for your current coding moment.
   - **Hover** the status bar item to read the full verse + the bridge line.
   - Select some code first to reflect specifically on what you're wrestling with.

## Settings
`resonate.engineUrl`, `resonate.translation`, `resonate.cadenceMinutes` (auto-surface interval; 0 = manual only), `resonate.enabled`.

## How it fits the architecture
This is one **delivery target** (`vscode`) of the Resonate engine. The same engine serves other
surfaces (Discord, wearable, …) — you choose where Scripture meets you. See the engine's
`ENGINE-DESIGN.md` and `resonate/delivery.py`.
