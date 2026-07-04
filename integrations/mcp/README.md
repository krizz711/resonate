# Resonate MCP server — Scripture as a capability for ANY assistant

The same engine that powers the browser extension, exposed over the **Model Context
Protocol** — the tool standard spoken by Claude, ChatGPT, Gemini and Copilot-class
assistants in 2026. The extension meets people on surfaces we don't control; MCP lets
**the assistants themselves** call Scripture natively. One engine, every AI.

Pure Python standard library (JSON-RPC 2.0 over stdio) — no SDK, no installs.

## Tools
| Tool | What the assistant gets |
|---|---|
| `resonate_verse` | a verified verse echoing the person's moment (+ bridge, confidence) — or an honest "stay silent"; crisis input returns help guidance, never a verse |
| `generate_story` | "your story": the person's moment woven into ONE vetted biblical narrative, labeled *not Scripture*, ending on the verse quoted verbatim |
| `fetch_passage` | verbatim licensed passage text by USFM ref (YouVersion in live mode) |

The guarantees are enforced **server-side**, whatever the model asks: safety gate first,
verse text only from the provider (never model memory), integrity labels on stories, and
per-user series memory that spans every surface ("you've returned to this 4× lately" —
even if yesterday was the extension and today is Claude).

## Hook it up

**Claude Desktop** — add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "resonate": {
      "command": "python",
      "args": ["C:/path/to/resonate/integrations/mcp/resonate_mcp.py"]
    }
  }
}
```

**Claude Code**:
```bash
claude mcp add resonate -- python integrations/mcp/resonate_mcp.py
```

**ChatGPT (developer mode)** — add a local MCP server pointing at the same command.

Then ask the assistant naturally: *"I'm exhausted and about to give up — is there
something in Scripture for this?"* → it calls `resonate_verse` / `generate_story` and
weaves the verified result into its answer.

## Smoke test (no client needed)
```bash
python integrations/mcp/smoke_client.py
```
Drives a real stdio session: initialize → tools/list → the three tools, and prints each result.
