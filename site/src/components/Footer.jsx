import { useState } from 'react'

// The MCP server block — the one thing a visitor pastes to give their own
// assistant Resonate's tools. Hosted URL first (nothing to install), matching
// connect.html; the personal ?key=RSN-… version is minted there.
const MCP_SNIPPET = `"mcpServers": {
  "resonate": {
    "url": "https://resonate-hg6j.onrender.com/mcp"
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
          Two ways in. Chat with AI in a <b>browser</b>? The{' '}
          <a href="/connect.html">extension</a> slips a quiet verse panel beside ChatGPT, Claude,
          Gemini, Grok and friends. Use a <b>coding assistant or Claude Desktop</b>? Resonate is a
          hosted <b>MCP server</b> — paste this URL block into any MCP config (or add it as a
          connector) and <b>Claude, Cursor, Copilot, Windsurf, Zed</b> can reach for a verified
          verse, weave a story, or pull reels, mid-conversation. Nothing to install.
        </p>

        <div className="mcp-card reveal">
          <div className="mcp-bar">
            <span className="mcp-file">any MCP config · hosted, no install</span>
            <button className="mcp-copy" onClick={copy} aria-live="polite">
              {copied ? '✓ Copied' : '⧉ Copy'}
            </button>
          </div>
          <pre><code>{MCP_SNIPPET}</code></pre>
        </div>
        <p className="mcp-after reveal">
          Then say <i>“I’m exhausted and losing hope.”</i> — your assistant calls{' '}
          <span className="mono-inline">resonate_verse</span> and answers with a real, cited verse.
          Mint a personal key on the <a href="/connect.html">connect page</a> and every AI you use
          shares one context.
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
