import { useEffect, useRef, useState } from 'react'

/* Radial orbital hub — plain-React adaptation of the shadcn
   radial-orbital-timeline: assistants orbit the Resonate core;
   clicking a node pauses the orbit and opens a detail card,
   clicking anywhere else resumes. Parchment-styled throughout. */

const ITEMS = [
  { title: 'Claude',  tag: 'MCP · native', desc: 'Resonate’s four tools appear natively in Claude — resonate_verse, generate_story, reel_groups and fetch_passage, straight from the tool list.' },
  { title: 'ChatGPT', tag: 'extension',    desc: 'The browser extension listens quietly and surfaces verified verses as gentle popups inside the conversation.' },
  { title: 'Gemini',  tag: 'MCP',          desc: 'Any client that speaks the Model Context Protocol calls the same engine — Gemini included, no separate build.' },
  { title: 'Discord', tag: 'bot',          desc: 'A community surface: verses and story reels arrive right inside your server, where the conversation already is.' },
  { title: 'VS Code', tag: 'MCP',          desc: 'Scripture where developers already work — the engine as an in-editor companion over the same protocol.' },
]

export default function OrbitalHub() {
  const [angle, setAngle] = useState(-90)
  const [active, setActive] = useState(null)
  const [size, setSize] = useState(400)
  const wrap = useRef(null)

  useEffect(() => {
    const ro = new ResizeObserver(([e]) => setSize(e.contentRect.width))
    ro.observe(wrap.current)
    return () => ro.disconnect()
  }, [])

  /* continuous orbit (~6°/s), paused while a node is open */
  useEffect(() => {
    if (active !== null) return
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let raf
    let last = performance.now()
    const tick = (now) => {
      setAngle((a) => (a + (now - last) * 0.006) % 360)
      last = now
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [active])

  const R = size * 0.37

  return (
    <div className="orbital" ref={wrap} onClick={() => setActive(null)}
      role="group" aria-label="Resonate as an MCP hub connected to five assistants">
      <div className="o-ring" aria-hidden="true" />
      <div className="o-ring r2" aria-hidden="true" />
      <div className="o-core" aria-hidden="true">
        <span className="ping" /><span className="ping p2" />
        <span className="r">R</span>
      </div>

      {ITEMS.map((it, i) => {
        const rad = ((i / ITEMS.length) * 360 + angle) * (Math.PI / 180)
        const x = Math.cos(rad) * R
        const y = Math.sin(rad) * R
        const depth = (1 + Math.sin(rad)) / 2
        const on = active === i
        return (
          <button
            key={it.title}
            className={`o-node${on ? ' on' : ''}`}
            style={{
              transform: `translate(${x}px, ${y}px) scale(${on ? 1.14 : 0.9 + depth * 0.14})`,
              opacity: on ? 1 : 0.7 + depth * 0.3,
              zIndex: on ? 40 : 20 + Math.round(depth * 10),
            }}
            onClick={(e) => { e.stopPropagation(); setActive(on ? null : i) }}
          >
            {it.title}
          </button>
        )
      })}

      {active !== null && (
        <div className="o-card" onClick={(e) => e.stopPropagation()}>
          <div className="oc-head">
            <span className="oc-title">{ITEMS[active].title}</span>
            <span className="oc-tag">{ITEMS[active].tag}</span>
          </div>
          <p>{ITEMS[active].desc}</p>
        </div>
      )}
    </div>
  )
}
