const ITEMS = ['ChatGPT', 'Claude', 'Gemini', 'VS Code', 'Discord']

function Row() {
  return (
    <div className="mitem">
      {ITEMS.map((it) => (
        <span key={it} style={{ display: 'contents' }}>
          <span>{it}</span><span className="st">✦</span>
        </span>
      ))}
      <span className="script">any MCP assistant</span><span className="st">✦</span>
    </div>
  )
}

export default function Marquee() {
  // rendered twice for a seamless -50% loop
  return (
    <div className="marquee" aria-hidden="true">
      <div className="mtrack">
        <Row />
        <Row />
      </div>
    </div>
  )
}
