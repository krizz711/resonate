export default function Footer() {
  return (
    <section id="try">
      <div className="bg-word" aria-hidden="true"><span>TRY</span></div>
      <div className="wrap">
        <div className="folio reveal">· VII ·</div>
        <div className="eyebrow reveal" style={{ justifyContent: 'center' }}><span className="tick" />See it move</div>
        <h2 className="display reveal">Try it — live, right now.</h2>
        <p className="lede reveal" style={{ margin: '16px auto 0' }}>
          The engine is deployed and running. Open the playground, type a worry, a question, a
          moment — and watch Scripture find its way in, or stay silent when it should.
        </p>
        <div className="try-actions reveal">
          <a className="btn primary" href="/playground.html" data-magnetic>Open the playground ↗</a>
          <a className="btn ghost" href="/mock-chat.html" data-magnetic>Demo chat</a>
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
