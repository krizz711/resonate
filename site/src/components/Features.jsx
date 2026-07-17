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
            <span className="chip">reel_groups</span>
            <span className="chip">fetch_passage</span>
          </div>
          <a className="btn primary" href="/connect.html" data-magnetic style={{ marginTop: '22px' }}>
            ⚡ Connect your assistant
          </a>
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
// Each chip plays the real Kokoro-rendered "godly" preset clip (public/voices/*.mp3),
// the exact audio shipped by resonate/tts.py — so a visitor hears our voices, not the
// browser's. The waveform lights up while the clip plays.
// NB: path is /voice-clips (not /voices) — the engine owns /voices for its JSON
// voice-list endpoint, and the Vite dev proxy forwards /voices there.
const VOICES = [
  { n: 'Bella', d: 'warm · close', src: '/voice-clips/bella.mp3' },
  { n: 'Isabella', d: 'luminous', src: '/voice-clips/isabella.mp3' },
  { n: 'George', d: 'natural · full', src: '/voice-clips/george.mp3' },
]

function Voices() {
  const [active, setActive] = useState(null)
  const [playing, setPlaying] = useState(false)
  const audioRef = useRef(null)

  // one reusable <audio>; created once so rapid taps never stack overlapping clips
  useEffect(() => {
    const a = new Audio()
    a.preload = 'none'
    audioRef.current = a
    const stop = () => { setPlaying(false); setActive(null) }
    a.addEventListener('ended', stop)
    a.addEventListener('error', stop) // missing/blocked file -> silently reset, never stuck
    return () => { a.pause(); a.removeEventListener('ended', stop); a.removeEventListener('error', stop) }
  }, [])

  const play = (i) => {
    const a = audioRef.current
    if (!a) return
    if (active === i && playing) {        // tap the playing voice again to stop it
      a.pause(); a.currentTime = 0; setPlaying(false); setActive(null); return
    }
    a.pause(); a.currentTime = 0
    a.src = VOICES[i].src
    setActive(i); setPlaying(true)
    a.play().catch(() => { setPlaying(false); setActive(null) })
  }

  return (
    <section id="voices">
      <div className="bg-word" aria-hidden="true"><span>VOICE</span></div>
      <div className="wrap act flip">
        <div className="copy reveal">
          <div className="folio-mark"><span className="num">II</span><span className="lbl">Voices</span></div>
          <h3 className="headline">Read aloud, like a voice from an old chapel.</h3>
          <p>
            Three Kokoro voices, tuned unhurried and reverent — warm, close, and slow.{' '}
            <span className="script">Tap a name</span> to hear the verse spoken in that voice, right
            here. In your assistant it can read every verse aloud by default, or only when you ask.
          </p>
          <div className="meta"><span className="chip">Kokoro TTS</span><span className="chip">auto-read optional</span></div>
        </div>
        <div className="visual reveal">
          <div className="stage" data-tilt>
            <div className={`voicebox${playing ? ' playing' : ''}`}>
              <div className="wave" aria-hidden="true">
                {Array.from({ length: 40 }, (_, i) => (
                  <i key={i} style={{ animationDelay: `${i * 0.045}s`, animationDuration: `${1.1 + (i % 5) * 0.16}s` }} />
                ))}
              </div>
              <div className="voice-verse">“Come unto me, all ye that labour and are heavy laden, and I will give you rest.”</div>
              <div className="voice-chips">
                {VOICES.map((v, i) => (
                  <button key={v.n} className={`vchip${active === i ? ' on' : ''}`} data-magnetic onClick={() => play(i)}
                    aria-label={active === i && playing ? `Stop ${v.n}` : `Hear ${v.n}`}>
                    <div className="vn">{v.n}</div>
                    <div className="vd">{active === i && playing ? '► playing' : v.d}</div>
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
            A verse is never written by the model. Each one is drawn from a curated, licensed
            library and quoted word-for-word, so nothing is invented. The engine is built to pair
            <b> Gloo AI</b>’s values-aligned reasoning with the <b>YouVersion Platform API</b> — so a
            real source always holds the exact words. Verbatim, or nothing, like a letter you break
            the seal on.
          </p>
          <div className="meta"><span className="chip">Gloo AI · YouVersion</span><span className="chip">verbatim · licensed</span><span className="chip">never model-written</span></div>
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
            verse — 100% recall on the eval set. And if you've registered <b>guardians</b>, it
            quietly reaches them by WhatsApp or email — consent-first, never sharing what you
            wrote. Restraint and rate-limiting keep it quiet; privacy by design keeps it local.
          </p>
          <div className="meta"><span className="chip">safety recall · 100%</span><span className="chip">guardian alerts · opt-in</span><span className="chip">no transcript kept</span></div>
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
  { kind: 'broomtree', label: 'Elijah · 1 Kings 19', verse: <>Under the broom tree, an angel said: <em>Arise and eat.</em></>, likes: '2.4k', notes: '318' },
  { kind: 'water', label: 'Peter · Matthew 14', verse: <>He walked on the water toward the voice that said <em>Come.</em></>, likes: '5.1k', notes: '602' },
  { kind: 'stillwaters', label: 'Psalm 23', verse: <>He leadeth me beside the still waters.</>, likes: '8.7k', notes: '914' },
  { kind: 'rest', label: 'Matthew 11:28', verse: <>Come to me, all who are weary — and I will give you rest.</>, likes: '3.9k', notes: '421' },
]

/* Hand-drawn 9:16 "poster" scenes — layered silhouettes over atmospheric gradients,
   so each reel shows real cover art instead of a flat wash. All inline SVG (no image
   files); gradient ids are per-scene so the four frames coexist in the DOM. */
function ReelScene({ kind }) {
  const common = { className: 'scene', viewBox: '0 0 160 340', preserveAspectRatio: 'xMidYMid slice', 'aria-hidden': true }
  if (kind === 'water') {
    return (
      <svg {...common}>
        <defs>
          <linearGradient id="wt-sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#0a1022" /><stop offset="60%" stopColor="#132339" /><stop offset="100%" stopColor="#1c3350" />
          </linearGradient>
          <linearGradient id="wt-beam" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fdf6df" stopOpacity=".55" /><stop offset="100%" stopColor="#fdf6df" stopOpacity="0" />
          </linearGradient>
        </defs>
        <rect width="160" height="340" fill="url(#wt-sky)" />
        <circle cx="80" cy="70" r="20" fill="#fbf3d8" /><circle cx="80" cy="70" r="34" fill="#fbf3d8" opacity=".08" />
        <g fill="#f4ead2" opacity=".7"><circle cx="30" cy="40" r=".9" /><circle cx="132" cy="52" r="1" /><circle cx="112" cy="28" r=".7" /></g>
        <rect y="176" width="160" height="164" fill="#0c1a2c" />
        <path d="M64 176 L96 176 L110 340 L50 340 Z" fill="url(#wt-beam)" />
        <g fill="#0a1524"><rect y="198" width="160" height="4" rx="2" opacity=".9" /><rect y="224" width="160" height="5" rx="2" opacity=".75" /><rect y="256" width="160" height="6" rx="3" opacity=".6" /></g>
        <path d="M78 210 q3 -18 3 -24 q0 -6 -2 -8 q6 0 6 8 q0 8 3 24 z" fill="#050b16" />
        <circle cx="80" cy="176" r="4.4" fill="#050b16" />
        <ellipse cx="80" cy="214" rx="15" ry="3" fill="#0a1524" opacity=".7" /><ellipse cx="80" cy="214" rx="8" ry="1.8" fill="#20415f" opacity=".5" />
      </svg>
    )
  }
  if (kind === 'stillwaters') {
    return (
      <svg {...common}>
        <defs>
          <linearGradient id="sw-sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#241826" /><stop offset="55%" stopColor="#5d4560" /><stop offset="100%" stopColor="#c88f66" />
          </linearGradient>
          <linearGradient id="sw-water" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#c88f66" stopOpacity=".85" /><stop offset="100%" stopColor="#33253a" />
          </linearGradient>
        </defs>
        <rect width="160" height="340" fill="url(#sw-sky)" />
        <circle cx="80" cy="198" r="27" fill="#f4d9a6" opacity=".5" /><circle cx="80" cy="202" r="10" fill="#f8e6c0" opacity=".9" />
        <path d="M0 208 Q46 188 92 200 Q130 210 160 196 V216 H0 Z" fill="#2e2130" />
        <path d="M0 214 Q60 202 160 214 V222 H0 Z" fill="#241826" />
        <rect y="220" width="160" height="120" fill="url(#sw-water)" />
        <rect x="72" y="220" width="16" height="120" fill="#f4d9a6" opacity=".2" />
        <g fill="#180f16">
          <path d="M40 220 q3 -20 4 -26 q0 -5 -3 -7 q7 -1 8 7 q1 8 3 26 z" />
          <circle cx="45" cy="184" r="4" />
        </g>
        <path d="M50 188 q8 -11 5 -22" stroke="#180f16" strokeWidth="1.6" fill="none" strokeLinecap="round" />
        <g fill="#241826" opacity=".85"><ellipse cx="64" cy="216" rx="5" ry="3" /><ellipse cx="76" cy="218" rx="4" ry="2.4" /></g>
      </svg>
    )
  }
  if (kind === 'rest') {
    return (
      <svg {...common}>
        <defs>
          <linearGradient id="rs-sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2a1c0c" /><stop offset="52%" stopColor="#7a5320" /><stop offset="100%" stopColor="#e6b45c" />
          </linearGradient>
          <radialGradient id="rs-sun" cx="50%" cy="74%" r="46%">
            <stop offset="0" stopColor="#fff2cf" /><stop offset="60%" stopColor="#f6cd7a" stopOpacity=".55" /><stop offset="100%" stopColor="#f6cd7a" stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width="160" height="340" fill="url(#rs-sky)" />
        <ellipse cx="80" cy="248" rx="120" ry="92" fill="url(#rs-sun)" />
        <g stroke="#fbe4ad" strokeWidth="1.1" opacity=".38" strokeLinecap="round">
          <line x1="80" y1="248" x2="80" y2="150" /><line x1="80" y1="248" x2="32" y2="178" /><line x1="80" y1="248" x2="128" y2="178" /><line x1="80" y1="248" x2="14" y2="238" /><line x1="80" y1="248" x2="146" y2="238" />
        </g>
        <circle cx="80" cy="250" r="21" fill="#fff4d6" />
        <path d="M0 268 Q54 244 160 264 V340 H0 Z" fill="#5a3d15" />
        <path d="M0 296 Q80 276 160 300 V340 H0 Z" fill="#3a2610" />
        <g fill="#1c1206"><path d="M74 268 q3 -18 4 -24 q0 -5 -3 -7 q7 -1 8 7 q1 8 3 24 z" /><circle cx="79" cy="234" r="4" /></g>
      </svg>
    )
  }
  // broomtree — Elijah, night desert with an angel's glow
  return (
    <svg {...common}>
      <defs>
        <linearGradient id="bt-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#0e1330" /><stop offset="52%" stopColor="#2a1d2a" /><stop offset="100%" stopColor="#3f2712" />
        </linearGradient>
        <radialGradient id="bt-glow" cx="50%" cy="74%" r="54%">
          <stop offset="0" stopColor="#ffce85" stopOpacity=".5" /><stop offset="100%" stopColor="#ffce85" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="160" height="340" fill="url(#bt-sky)" />
      <g fill="#f4ead2"><circle cx="26" cy="46" r="1" /><circle cx="128" cy="30" r="1.1" /><circle cx="60" cy="34" r=".7" /><circle cx="96" cy="66" r=".8" /><circle cx="18" cy="86" r=".7" /></g>
      <circle cx="120" cy="56" r="13" fill="#f7eecf" /><circle cx="120" cy="56" r="24" fill="#f7eecf" opacity=".1" />
      <ellipse cx="82" cy="256" rx="80" ry="66" fill="url(#bt-glow)" />
      <path d="M0 258 Q66 230 160 254 V340 H0 Z" fill="#26180a" />
      <path d="M0 290 Q86 266 160 298 V340 H0 Z" fill="#150d05" />
      <g fill="#0d0904">
        <path d="M95 256 C92 226 90 208 92 188 C96 208 99 232 101 256 Z" />
        <ellipse cx="88" cy="184" rx="19" ry="8" /><ellipse cx="103" cy="192" rx="13" ry="6" /><ellipse cx="97" cy="176" rx="11" ry="5" />
      </g>
      <path d="M66 256 q-2 -12 6 -16 q8 -3 11 5 q2 7 -2 11 z" fill="#0b0703" />
    </svg>
  )
}

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
            the passage — and reels arrive in small <b>sets, ordered for you</b>: for this moment,
            threads you return to, steady ground. Each set carries a line about why it found you.
          </p>
          <div className="meta"><span className="chip">9:16 · shareable</span><span className="chip">sets · priority I·II·III</span><a className="chip" href="/reels.html" title="Open your recommended reel sets">▷ open your reels</a></div>
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
                        <ReelScene kind={f.kind} />
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

/* ---------- 6. Scripture Guide ---------- */
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
      <div className="bg-word" aria-hidden="true"><span>GUIDE</span></div>
      <div className="wrap act flip">
        <div className="copy reveal">
          <div className="folio-mark"><span className="num">VI</span><span className="lbl">Scripture Guide</span></div>
          <h3 className="headline">Ask deeper — by chat, or by phone.</h3>
          <p>
            Talk with <span className="script">Scripture Guide</span>, an assistant tuned for
            scriptural knowledge and honest debate — Gloo AI's aligned models on the line.
            Reachable in chat, by voice message, or a real phone call through an n8n automation.
          </p>
          <div className="meta"><span className="chip">chat · voice</span><span className="chip">n8n · Gloo AI</span><a className="chip" href="/guide.html" title="Chat with Ezra, or call him by voice">☎ talk to Ezra</a></div>
        </div>
        <div className="visual reveal">
          <div className="stage" data-tilt>
            <div className="master">
              <div className="mchat">
                <div className="mbub me">Is doubt the opposite of faith?</div>
                <div className="mbub sm">
                  <div className="who">Scripture Guide</div>
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
