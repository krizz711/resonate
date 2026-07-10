import { useEffect } from 'react'
import HeroStatue3D from './HeroStatue3D'

const TAGLINES = [
  'Scripture, where you already are.',
  'It only speaks when it hears a story.',
  'A voice from an old chapel.',
  'Your story, woven from a real one.',
  'And when it hears darkness — it sends people, not verses.',
]

// Page 1 — asymmetric split hero.
// Left: the brand writes itself in letter by letter, rotating taglines
// (same rotation as the deployed playground), the hook as sub-copy, CTAs.
// Right: the 3D Christus stands clean against the cream, nothing over it.
export default function Hero() {
  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const spans = Array.from(document.querySelectorAll('.hero-left .tagline span'))
    if (spans.length < 2) return
    let i = 0
    const id = setInterval(() => {
      spans[i].classList.remove('in'); spans[i].classList.add('out')
      const prev = i; i = (i + 1) % spans.length
      spans[i].classList.remove('out'); spans[i].classList.add('in')
      setTimeout(() => spans[prev].classList.remove('out'), 850)
    }, 3600)
    return () => clearInterval(id)
  }, [])

  return (
    <section id="hero">
      <div className="hero-canvas" aria-hidden="true" />
      <div className="hero-scene" aria-hidden="true">
        <div className="hero-scene-img" />
        <div className="hero-scene-rays" />
        <div className="hero-scene-veil" />
      </div>
      <HeroStatue3D />

      <div className="hero-left">
        <h1 className="ht-name" aria-label="Resonate">
          <span className="cross ch">†</span>
          {'Resonate'.split('').map((c, i) => (
            <span className="ch" key={i}>{c}</span>
          ))}
        </h1>
        <div className="tagline" aria-live="polite">
          {TAGLINES.map((t, i) => (
            <span key={t} className={i === 0 ? 'in' : ''}>{t}</span>
          ))}
        </div>
        <p className="hero-copy">
          Billions type their most honest words into an AI — not a Bible app.
          <b> Resonate</b> brings context, truth, and Scripture directly into
          your daily AI conversations and workflows.
        </p>
        <div className="hero-ctas">
          <a className="btn primary" href="/playground.html" data-magnetic>⚡ Add to Claude / ChatGPT</a>
          <a className="btn ghost" href="#features" data-magnetic>📖 Explore the features</a>
        </div>
      </div>
    </section>
  )
}
