import { useEffect, useId, useRef, useState } from 'react'
import OrbitalHub from './OrbitalHub'

/* rotating circular-text badge, wax seal at its heart — overlaps each stage */
function Stamp() {
  const arc = `arc-${useId().replace(/[^a-zA-Z0-9-]/g, '')}`
  return (
    <div className="stamp" aria-hidden="true">
      <svg viewBox="0 0 120 120">
        <defs>
          <path id={arc} d="M60,60 m-47,0 a47,47 0 1,1 94,0 a47,47 0 1,1 -94,0" />
        </defs>
        <text>
          <textPath href={`#${arc}`}>Scripture · in new frontiers · Resonate ·</textPath>
        </text>
      </svg>
      <div className="stamp-core">R</div>
    </div>
  )
}

/* ---------- intro ---------- */
function Intro() {
  return (
    <section id="features">
      <div className="bg-word" aria-hidden="true"><span>SIX</span></div>
      <div className="count reveal" aria-hidden="true">VI</div>
      <div className="eyebrow reveal" style={{ justifyContent: 'center' }}><span className="tick" />The capabilities</div>
      <h2 className="display reveal">Six quiet ways it meets you.</h2>
      <p className="lede reveal">
        One engine, many native surfaces — safety first, verses verbatim, stories labeled, memory
        that spans surfaces.
      </p>
    </section>
  )
}

/* ---------- 1. MCP hub ---------- */
function Mcp() {
  return (
    <section id="mcp">
      <div className="bg-word" aria-hidden="true"><span>CONNECT</span></div>
      <div className="wrap act">
        <div className="copy reveal">
          <div className="folio-mark"><span className="num">I</span><span className="lbl">Connect anywhere</span></div>
          <h3 className="headline">Scripture as a capability — for any assistant.</h3>
          <p>
            Resonate ships as an <b>MCP server</b>. Claude, ChatGPT, Gemini, Discord, VS Code — any
            tool that speaks the Model Context Protocol calls the same engine natively. One hub,
            every surface a spoke.
          </p>
          <div className="meta">
            <span className="chip">resonate_verse</span>
            <span className="chip">generate_story</span>
            <span className="chip">fetch_passage</span>
          </div>
        </div>
        <div className="visual reveal">
          <div className="stage" data-tilt>
            <OrbitalHub />
          </div>
          <Stamp />
        </div>
      </div>
    </section>
  )
}

/* ---------- 2. Voices ---------- */
const VOICES = [
  { n: 'Bella', d: 'warm · close' },
  { n: 'Isabella', d: 'luminous' },
  { n: 'George', d: 'natural · full' },
]

function Voices() {
  const [active, setActive] = useState(null)
  const [playing, setPlaying] = useState(false)
  const timer = useRef()

  const play = (i) => {
    setActive(i); setPlaying(true)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => { setPlaying(false); setActive(null) }, 3200)
  }
  useEffect(() => () => clearTimeout(timer.current), [])

  return (
    <section id="voices">
      <div className="bg-word" aria-hidden="true"><span>VOICE</span></div>
      <div className="wrap act flip">
        <div className="copy reveal">
          <div className="folio-mark"><span className="num">II</span><span className="lbl">Voices</span></div>
          <h3 className="headline">Read aloud, like a voice from an old chapel.</h3>
          <p>
            Three voices, synthesized locally with Kokoro, tuned unhurried and reverent. Press{' '}
            <span className="script">Listen</span> and the verse is spoken — warm, close, and slow.
            Play by default, or only when you ask.
          </p>
          <div className="meta"><span className="chip">Kokoro TTS · on-device</span><span className="chip">auto-read optional</span></div>
        </div>
        <div className="visual reveal">
          <div className="stage" data-tilt>
            <div className={`voicebox${playing ? ' playing' : ''}`}>
              <div className="wave" aria-hidden="true">
                {Array.from({ length: 40 }, (_, i) => (
                  <i key={i} style={{ animationDelay: `${i * 0.045}s`, animationDuration: `${1.1 + (i % 5) * 0.16}s` }} />
                ))}
              </div>
              <div className="voice-verse">“Come to me, all you who are weary and burdened, and I will give you rest.”</div>
              <div className="voice-chips">
                {VOICES.map((v, i) => (
                  <button key={v.n} className={`vchip${active === i ? ' on' : ''}`} data-magnetic onClick={() => play(i)}>
                    <div className="vn">{v.n}</div><div className="vd">{v.d}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
          <Stamp />
        </div>
      </div>
    </section>
  )
}

/* ---------- 3. Verses / wax seal ---------- */
function Verses() {
  return (
    <section id="verses">
      <div className="bg-word" aria-hidden="true"><span>WORD</span></div>
      <div className="wrap act">
        <div className="copy reveal">
          <div className="folio-mark"><span className="num">III</span><span className="lbl">Verses</span></div>
          <h3 className="headline">Verified words, sealed until they’re yours.</h3>
          <p>
            The model proposes a reference from a vetted shortlist; the <b>YouVersion Platform API</b>
            {' '}confirms the words. Nothing is ever hallucinated — every verse arrives licensed and
            verbatim, like a letter you break the seal on.
          </p>
          <div className="meta"><span className="chip">verbatim · licensed</span><span className="chip">131 curated refs</span></div>
        </div>
        <div className="visual reveal">
          <div className="stage" data-tilt>
            <div className="sealcard" id="sealcard">
              <div className="sreveal">
                <div className="sref">Psalm 23:3 · KJV</div>
                <div className="sverse">He restoreth my soul: he leadeth me in the paths of righteousness for his name’s sake.</div>
                <div className="ssrc">YouVersion · verified · licensed</div>
              </div>
              <div className="bigseal" id="bigseal" aria-hidden="true">R</div>
            </div>
          </div>
          <Stamp />
        </div>
      </div>
    </section>
  )
}

/* ---------- 4. Safety ---------- */
function Safety() {
  return (
    <section id="safety">
      <div className="bg-word" aria-hidden="true"><span>SAFE</span></div>
      <div className="wrap act flip">
        <div className="copy reveal">
          <div className="folio-mark"><span className="num">IV</span><span className="lbl">Security &amp; safety</span></div>
          <h3 className="headline">When it hears darkness, it sends people — not verses.</h3>
          <p>
            Crisis text is caught on the raw input and routed to a <b>human-help card</b>, never a
            verse — 100% recall on the eval set. Restraint and rate-limiting keep it quiet; privacy
            by design keeps it local. It reads only your own message and stores nothing.
          </p>
          <div className="meta"><span className="chip">safety recall · 100%</span><span className="chip">stores nothing</span><span className="chip">rate-limited</span></div>
        </div>
        <div className="visual reveal">
          <div className="stage" data-tilt>
            <div className="safety">
              <svg className="shield" viewBox="0 0 120 140" aria-hidden="true">
                <path className="fillc" d="M60 8 L108 26 V70 C108 104 86 124 60 132 C34 124 12 104 12 70 V26 Z" />
                <path className="draw" d="M60 8 L108 26 V70 C108 104 86 124 60 132 C34 124 12 104 12 70 V26 Z" />
                <path className="draw" d="M42 70 L55 84 L82 54" />
              </svg>
              <div className="helpcard">
                <div className="hr">A pause, not a verse</div>
                <div className="ht">This sounds heavy, and a verse isn’t the right response here. Please reach out to someone you trust, or a crisis line.</div>
                <div className="hf">Resonate · your wellbeing comes first</div>
              </div>
            </div>
          </div>
          <Stamp />
        </div>
      </div>
    </section>
  )
}

/* ---------- 5. Story reels ---------- */
const FRAMES = [
  { scene: 'radial-gradient(120% 90% at 50% 20%,#8a6a3a,#141008)', label: 'Elijah · 1 Kings 19', verse: <>Under the broom tree, an angel said: <em>Arise and eat.</em></>, likes: '2.4k', notes: '318' },
  { scene: 'radial-gradient(120% 90% at 50% 30%,#3a5570,#0b0e12)', label: 'Peter · Matthew 14', verse: <>He walked on the water toward the voice that said <em>Come.</em></>, likes: '5.1k', notes: '602' },
  { scene: 'radial-gradient(120% 90% at 50% 25%,#6d4a63,#100a10)', label: 'Psalm 23', verse: <>He leadeth me beside the still waters.</>, likes: '8.7k', notes: '914' },
  { scene: 'radial-gradient(120% 90% at 50% 20%,#87652a,#141008)', label: 'Matthew 11:28', verse: <>Come to me, all who are weary — and I will give you rest.</>, likes: '3.9k', notes: '421' },
]

/* tiny reel-UI glyphs for the action rail */
const IconHeart = () => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21S3.5 15.4 3.5 9.3C3.5 6.4 5.7 4.5 8.2 4.5c1.7 0 3 .9 3.8 2.1.8-1.2 2.1-2.1 3.8-2.1 2.5 0 4.7 1.9 4.7 4.8C20.5 15.4 12 21 12 21Z" /></svg>)
const IconChat = () => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.5 4.5h15A1.5 1.5 0 0 1 21 6v9a1.5 1.5 0 0 1-1.5 1.5H9l-4.2 3.4A.6.6 0 0 1 3.8 19V6a1.5 1.5 0 0 1 1.5-1.5Z" /></svg>)
const IconShare = () => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 20.5 21.5 12 3 3.5 3 10l12 2-12 2 0 6.5Z" /></svg>)

function Reels() {
  const [active, setActive] = useState(0)
  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const id = setInterval(() => setActive((a) => (a + 1) % FRAMES.length), 2600)
    return () => clearInterval(id)
  }, [])

  return (
    <section id="reels">
      <div className="bg-word" aria-hidden="true"><span>REELS</span></div>
      <div className="wrap act">
        <div className="copy reveal">
          <div className="folio-mark"><span className="num">V</span><span className="lbl">Story reels</span></div>
          <h3 className="headline">Every verse carries a doorway.</h3>
          <p>
            One tap turns the moment into a short vertical <span className="script">story film</span> of
            the passage — the format we pitch for YouVersion and partners to host. The verse moves
            from a quiet popup to something you carry.
          </p>
          <div className="meta"><span className="chip">9:16 · shareable</span><span className="chip">labeled reflection</span></div>
        </div>
        <div className="visual reveal">
          <div className="stage" data-tilt>
            <div className="reelscene">
              <div className="rs-disc" aria-hidden="true" />

              {/* front phone — the live scripture reel feed */}
              <div className="rp rp-front">
                <div className="rp-frame">
                  <span className="rp-cam" aria-hidden="true" />
                  <div className="rp-screen">
                    <div className="reel-bars">
                      {FRAMES.map((_, k) => (
                        <span className="b" key={k}>
                          <i key={`${k}-${active}`} className={k < active ? 'done' : k === active ? 'run' : ''} style={{ '--rdur': '2600ms' }} />
                        </span>
                      ))}
                    </div>
                    {FRAMES.map((f, k) => (
                      <div className={`reel-frame${k === active ? ' on' : ''}`} key={k}>
                        <div className="scene" style={{ background: f.scene }} />
                        <div className="rlabel">{f.label}</div>
                        <div className="rverse">{f.verse}</div>
                      </div>
                    ))}
                    <div className="rp-rail" aria-hidden="true">
                      <span className="ra-av">R</span>
                      <span className="ra"><IconHeart /><b>{FRAMES[active].likes}</b></span>
                      <span className="ra"><IconChat /><b>{FRAMES[active].notes}</b></span>
                      <span className="ra"><IconShare /><b>Share</b></span>
                    </div>
                    <div className="rp-nav" aria-hidden="true">
                      <i /><i /><span className="rp-plus">+</span><i /><i />
                    </div>
                  </div>
                </div>
              </div>

              {/* back phone — Resonate splash */}
              <div className="rp rp-back">
                <div className="rp-frame">
                  <span className="rp-cam" aria-hidden="true" />
                  <div className="rp-screen rp-splash">
                    <div className="rp-seal">R</div>
                    <div className="rp-brand">Resonate</div>
                    <div className="rp-tag">· story reels ·</div>
                  </div>
                </div>
              </div>
            </div>
            <div className="reel-cap">Scripture, told as story — one tap turns a verse into a reel.</div>
          </div>
          <Stamp />
        </div>
      </div>
    </section>
  )
}

/* ---------- 6. Scripture Master ---------- */
function Master() {
  const [s, setS] = useState(12)
  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const id = setInterval(() => setS((v) => v + 1), 1000)
    return () => clearInterval(id)
  }, [])
  const mm = String(Math.floor(s / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')

  return (
    <section id="master">
      <div className="bg-word" aria-hidden="true"><span>MASTER</span></div>
      <div className="wrap act flip">
        <div className="copy reveal">
          <div className="folio-mark"><span className="num">VI</span><span className="lbl">Scripture Master</span></div>
          <h3 className="headline">Ask deeper — by chat, or by phone.</h3>
          <p>
            Talk with <span className="script">Scripture Master</span>, an assistant tuned for
            scriptural knowledge and honest debate. Reachable in chat — or by a real phone call
            through an n8n voice automation. The same engine, now on the line.
          </p>
          <div className="meta"><span className="chip">chat</span><span className="chip">voice call · n8n</span></div>
        </div>
        <div className="visual reveal">
          <div className="stage" data-tilt>
            <div className="master">
              <div className="mchat">
                <div className="mbub me">Is doubt the opposite of faith?</div>
                <div className="mbub sm">
                  <div className="who">Scripture Master</div>
                  Not quite — Scripture treats doubt as a doorway.{' '}
                  <span className="script">“Lord, I believe; help my unbelief.”</span> (Mark 9:24)
                  Shall we sit with that?
                </div>
                <div className="mbub me">Yes. Where does it lead?</div>
              </div>
              <div className="callpanel">
                <div className="ringbox" aria-hidden="true">
                  <span className="rw" /><span className="rw" /><span className="rw" />
                  <span className="core">
                    <svg viewBox="0 0 24 24" fill="none">
                      <path d="M6.5 3.5 9 3l1.5 4-2 1.5a11 11 0 0 0 5 5L14 11l4 1.5-.5 2.5A2 2 0 0 1 15 17 13 13 0 0 1 4 6a2 2 0 0 1 2.5-2.5Z" fill="#f3e4d5" />
                    </svg>
                  </span>
                </div>
                <div className="cstate">On the line</div>
                <div className="ctime">{mm}:{ss}</div>
                <div className="cwave" aria-hidden="true">
                  {[0, 0.1, 0.2, 0.15, 0.05, 0.25].map((d, i) => (
                    <i key={i} style={{ animationDelay: `${d}s` }} />
                  ))}
                </div>
              </div>
            </div>
          </div>
          <Stamp />
        </div>
      </div>
    </section>
  )
}

export default function Features() {
  return (
    <>
      <Intro />
      <Mcp />
      <Voices />
      <Verses />
      <Safety />
      <Reels />
      <Master />
    </>
  )
}
