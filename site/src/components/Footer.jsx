import { useState } from 'react'

// The MCP server block — the one thing a visitor pastes to give their own
// assistant Resonate's tools. Kept in the exact shape connect.html teaches.
const MCP_SNIPPET = `"mcpServers": {
  "resonate": {
    "command": "python",
    "args": ["C:/path/to/resonate/integrations/mcp/resonate_mcp.py"]
  }
}`

export default function Footer() {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    const done = () => { setCopied(true); setTimeout(() => setCopied(false), 2200) }
    try {
      navigator.clipboard.writeText(MCP_SNIPPET).then(done, done)
    } catch (e) { done() }
  }

  return (
    <section id="try">
      <div className="bg-word" aria-hidden="true"><span>CONNECT</span></div>
      <div className="wrap">
        <div className="folio reveal">· VII ·</div>
        <div className="eyebrow reveal" style={{ justifyContent: 'center' }}><span className="tick" />Enable your assistant</div>
        <h2 className="display reveal">Give your assistant a sense of Scripture.</h2>
        <p className="lede reveal" style={{ margin: '16px auto 0' }}>
          Resonate runs as an <b>MCP server</b> — paste this block into your assistant&apos;s MCP
          config (Claude Desktop: <span className="mono-inline">Settings → Developer → Edit Config</span>),
          use the real path on your machine, restart — and <b>Claude, Gemini, ChatGPT, Copilot,
          Cursor, Antigravity, Windsurf</b> — any MCP-speaking app — can reach for a verified
          verse, weave a story, or pull reels, mid-conversation.
        </p>

        <div className="mcp-card reveal">
          <div className="mcp-bar">
            <span className="mcp-file">claude_desktop_config.json</span>
            <button className="mcp-copy" onClick={copy} aria-live="polite">
              {copied ? '✓ Copied' : '⧉ Copy'}
            </button>
          </div>
          <pre><code>{MCP_SNIPPET}</code></pre>
        </div>
        <p className="mcp-after reveal">
          Then say <i>“I’m exhausted and losing hope.”</i> — your assistant calls{' '}
          <span className="mono-inline">resonate_verse</span> and answers with a real, cited verse.
        </p>

        <div className="try-actions reveal">
          <a className="btn primary" href="/connect.html" data-magnetic>⚡ Full setup for your app ↗</a>
          <a className="btn ghost" href="/panel-preview.html" data-magnetic>Panel preview</a>
          <a className="btn ghost" href="https://github.com/krizz711/resonate" target="_blank" rel="noopener" data-magnetic>Source · GitHub</a>
        </div>
        <div className="credits reveal">
          <b>Resonate</b> · Scripture, where you already are · built for the Kaggle challenge{' '}
          <span className="em">“Scripture in New Frontiers”</span><br />
          Powered by the <b>YouVersion Platform API</b> (every verse verbatim &amp; licensed) and{' '}
          <b>Gloo AI Studio</b> (values-aligned reasoning) · MIT licensed<br />
          Privacy: reads only your own message, keeps no transcript — only theme patterns, on your
          machine · Crisis input is answered with human help, never verses
        </div>
      </div>
    </section>
  )
}
