import { useRef, useEffect } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useGSAP } from '@gsap/react'
import { initSmoothScroll } from './lib/smoothScroll'

import Nav from './components/Nav'
import Hero from './components/Hero'
import Marquee from './components/Marquee'
import Features from './components/Features'
import Stats from './components/Stats'
import Footer from './components/Footer'

gsap.registerPlugin(useGSAP, ScrollTrigger)

export default function App() {
  const root = useRef(null)

  // Lenis smooth-scroll wired to GSAP ticker for buttery 60 fps feel
  useEffect(() => {
    const cleanup = initSmoothScroll()
    return cleanup
  }, [])

  useGSAP(() => {
    const el = root.current
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
    const q = (sel) => Array.from(el.querySelectorAll(sel))

    if (reduce) {
      q('.reveal').forEach((n) => { n.style.opacity = 1; n.style.transform = 'none' })
      q('.shield .draw').forEach((p) => { p.style.strokeDashoffset = 0 })
      q('.eyebrow .tick').forEach((t) => { t.style.width = '28px' })
      q('[data-count]').forEach((n) => { n.innerText = n.dataset.count })
      q('.pause-beam').forEach((n) => { n.style.transform = 'scaleY(1)' })
      q('.pause-seal, .pause-rule').forEach((n) => { n.style.opacity = 1; n.style.transform = 'none' })
      return
    }

    const cleanups = []

    /* ── Stage 1 → 2: Hero pinned + all-edge cinematic dissolve ─────────
       Phase 1 (0–38% of pin scroll): hero stays completely static.
       Phase 2 (38–100%): clip-path closes from ALL four edges simultaneously
       — visibly from top AND bottom — squeezing the image into a thin pill
       shape that collapses to nothing, dissolving into the cream background.
       Total pin distance ≈ 2.5× viewport height for a satisfying long hold. */
    const heroDissolve = gsap.timeline({
      scrollTrigger: {
        trigger: '#hero',
        start: 'top top',
        end: () => `+=${window.innerHeight * 1.6}`,
        pin: true,
        anticipatePin: 1,
        scrub: 0.4,
        invalidateOnRefresh: true,
      },
    })
    heroDissolve
      .set('#hero', { clipPath: 'ellipse(120% 110% at 50% 50%)' })
      .to('#hero', { clipPath: 'ellipse(0% 0% at 50% 50%)', duration: 1, ease: 'power2.inOut' })

    /* the manuscript frame sits over the page (z2) but must never cover the
       hero scene — it materialises as the hero dissolves, reversing on the
       way back up (scrubbed with the same trigger) */
    gsap.set('.page-frame', { opacity: 0 })
    heroDissolve.to('.page-frame', { opacity: 1, duration: 0.4, ease: 'power1.in' }, 0.6)

    /* ── hero → content bridge — as the hero collapses, a shaft of light
       descends into a wax seal and an ornamental divider opens the acts ── */
    gsap.set('.pause-beam', { scaleY: 0, transformOrigin: '50% 0%' })
    gsap.set('.pause-seal, .pause-rule', { opacity: 0, y: 12 })
    gsap.timeline({
      scrollTrigger: { trigger: '.hero-pause', start: 'top 82%', end: 'top 34%', scrub: 0.6 },
    })
      .to('.pause-beam', { scaleY: 1, ease: 'none' })
      .to('.pause-seal', { opacity: 1, y: 0, ease: 'power2.out' }, '-=.15')
      .to('.pause-rule', { opacity: 1, y: 0, ease: 'power2.out' }, '-=.25')

    /* ── manuscript frame — the fixed margins drift a touch slower than the
       page across the whole scroll, like a plate the story turns beneath ── */
    gsap.fromTo('.page-frame .pf',
      { y: () => window.innerHeight * 0.02 },
      { y: () => window.innerHeight * -0.02, ease: 'none',
        scrollTrigger: { trigger: 'main', start: 'top top', end: 'bottom bottom', scrub: 1.2, invalidateOnRefresh: true } })

    /* ── generic reveals — every .reveal outside the hero ──
       Elements with a signature entrance of their own (act visuals, the
       aim statement, the roman-numeral count, the stat band) are skipped:
       they're choreographed individually further down. */
    q('.reveal').forEach((n) => {
      if (n.closest('#hero')) return
      if (n.matches('.act .visual, #features .count, .stat')) return
      gsap.set(n, { opacity: 0, y: 34 })
      ScrollTrigger.create({
        trigger: n, start: 'top 86%', once: true,
        onEnter: () => gsap.to(n, { opacity: 1, y: 0, duration: 1.05, ease: 'power3.out' }),
      })
    })

    /* ── Giant section words — editorial parallax, one direction each ────
       Every word travels on its own vector — vertical, horizontal, or
       with a slow rotation — so no two sections scroll the same way.
       All are cropped by section edges like oversized print. */
    const DRIFTS = {
      features: [{ yPercent: 60 }, { yPercent: -60 }],
      mcp:      [{ xPercent: -14 }, { xPercent: 14 }],
      voices:   [{ yPercent: 55, rotate: 2.5 }, { yPercent: -55, rotate: -2.5 }],
      verses:   [{ xPercent: 14, rotate: -1.5 }, { xPercent: -14, rotate: 1.5 }],
      safety:   [{ yPercent: -55 }, { yPercent: 55 }],
      reels:    [{ xPercent: -14, rotate: 2 }, { xPercent: 14, rotate: -2 }],
      master:   [{ yPercent: 60 }, { yPercent: -60 }],
      try:      [{ yPercent: 45, scale: 0.9 }, { yPercent: -25, scale: 1.15 }],
    }
    q('.bg-word span').forEach((span) => {
      const section = span.closest('section')
      const [from, to] = DRIFTS[section.id] || [{ yPercent: 60 }, { yPercent: -60 }]
      gsap.fromTo(span, from, {
        ...to,
        ease: 'none',
        scrollTrigger: { trigger: section, start: 'top bottom', end: 'bottom top', scrub: 0.6 },
      })
    })

    /* scroll-velocity skew — the big words shear slightly with fast
       scrolling and settle back, giving the type a fluid, inky feel */
    const words = q('.bg-word span')
    if (words.length) {
      const setters = words.map((w) => gsap.quickSetter(w, 'skewY', 'deg'))
      const skew = { v: 0 }
      const apply = () => setters.forEach((s) => s(skew.v))
      ScrollTrigger.create({
        onUpdate: (self) => {
          const target = gsap.utils.clamp(-2.5, 2.5, self.getVelocity() / -500)
          if (Math.abs(target) > Math.abs(skew.v)) {
            skew.v = target
            gsap.to(skew, { v: 0, duration: 0.9, ease: 'power3.out', overwrite: true, onUpdate: apply })
          }
        },
      })
    }

    /* ── layered depth: each act's visual drifts slower than the copy ── */
    q('.act .visual').forEach((v) => {
      gsap.fromTo(v,
        { y: 44 },
        {
          y: -44,
          ease: 'none',
          scrollTrigger: { trigger: v.closest('section'), start: 'top bottom', end: 'bottom top', scrub: 0.8 },
        }
      )
    })

    /* ── signature entrances — every act arrives differently ─────────────
       The drift above owns `y` on the visuals, so entrances only use
       x / scale / rotation / clip-path — no two tweens fight a property. */
    const enter = (trigger, build, start = 'top 68%') => {
      const tl = gsap.timeline({ paused: true })
      build(tl)
      ScrollTrigger.create({ trigger, start, once: true, onEnter: () => tl.play() })
    }
    /* each act's wax stamp presses down onto the page at the end */
    gsap.set('.stamp', { opacity: 0, scale: 1.55, rotate: -12 })
    const press = (tl, sel) =>
      tl.to(sel, { opacity: 1, scale: 1, rotate: 0, duration: 0.55, ease: 'back.out(2.2)' }, '-=.3')

    /* hero intro — the name writes itself in glyph by glyph like wet ink,
       then tagline, hook copy and CTAs settle in beneath it in order */
    gsap.set('.ht-name .ch', { opacity: 0, y: 12, filter: 'blur(4px)' })
    gsap.set('.hero-left .tagline', { opacity: 0 })
    gsap.set('.hero-copy, .hero-ctas', { opacity: 0, y: 22 })
    gsap.timeline({ delay: 0.5 })
      .to('.ht-name .ch', { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.5, stagger: 0.11, ease: 'power2.out' })
      .to('.hero-left .tagline', { opacity: 1, duration: 0.9, ease: 'power2.out' }, '-=.15')
      .to('.hero-copy, .hero-ctas', { opacity: 1, y: 0, duration: 0.9, ease: 'power3.out', stagger: 0.16 }, '-=.5')

    /* VI — the roman numeral stamps down as the intro approaches */
    gsap.fromTo('#features .count',
      { scale: 2.1, opacity: 0 },
      { scale: 1, opacity: 1, ease: 'none',
        scrollTrigger: { trigger: '#features', start: 'top 92%', end: 'top 42%', scrub: 0.5 } })

    /* 1 · Connect — an iris opens on the hub */
    gsap.set('#mcp .stage', { opacity: 0, clipPath: 'circle(6% at 50% 50%)' })
    enter('#mcp', (tl) => {
      tl.to('#mcp .stage', { opacity: 1, clipPath: 'circle(75% at 50% 50%)', duration: 1.25, ease: 'power3.inOut', clearProps: 'clipPath' })
      press(tl, '#mcp .stamp')
    })

    /* 2 · Voices — swells up from silence, elastic like a note */
    gsap.set('#voices .visual', { opacity: 0, scale: 0.8, transformOrigin: '50% 85%' })
    enter('#voices', (tl) => {
      tl.to('#voices .visual', { opacity: 1, scale: 1, duration: 1.45, ease: 'elastic.out(1,0.5)' })
      press(tl, '#voices .stamp')
    })

    /* 3 · Verses — the sealed card swings open like a letter */
    gsap.set('#verses .visual', { opacity: 0, rotationY: -55, transformPerspective: 1000, transformOrigin: '0% 50%' })
    enter('#verses', (tl) => {
      tl.to('#verses .visual', { opacity: 1, rotationY: 0, duration: 1.5, ease: 'power4.out' })
      press(tl, '#verses .stamp')
    })

    /* 4 · Safety — the shield wipes down like a lowered guard,
       then the help card surfaces */
    gsap.set('#safety .stage', { clipPath: 'inset(0 0 100% 0)' })
    gsap.set('#safety .helpcard', { opacity: 0, y: 26 })
    enter('#safety', (tl) => {
      tl.to('#safety .stage', { clipPath: 'inset(0 0 0% 0)', duration: 1.1, ease: 'power4.inOut', clearProps: 'clipPath' })
        .to('#safety .helpcard', { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out' }, '-=.3')
      press(tl, '#safety .stamp')
    })

    /* 5 · Reels — the phone slides in from the wings, straightening */
    gsap.set('#reels .visual', { opacity: 0, x: 150, rotation: 7 })
    enter('#reels', (tl) => {
      tl.to('#reels .visual', { opacity: 1, x: 0, rotation: 0, duration: 1.3, ease: 'power4.out' })
      press(tl, '#reels .stamp')
    })

    /* 6 · Master — the conversation assembles bubble by bubble,
       then the call panel rings in */
    gsap.set('#master .stage', { opacity: 0 })
    gsap.set('#master .mbub', { opacity: 0, y: 24, scale: 0.9 })
    gsap.set('#master .callpanel', { opacity: 0, scale: 0.8, transformOrigin: '50% 60%' })
    enter('#master', (tl) => {
      tl.to('#master .stage', { opacity: 1, duration: 0.6, ease: 'power2.out' })
        .to('#master .mbub', { opacity: 1, y: 0, scale: 1, duration: 0.55, ease: 'power3.out', stagger: 0.2 }, '-=.2')
        .to('#master .callpanel', { opacity: 1, scale: 1, duration: 0.8, ease: 'back.out(1.7)' }, '-=.25')
      press(tl, '#master .stamp')
    })

    /* stats — the whole band counts in as one strip, left to right */
    gsap.set('.stat', { opacity: 0, y: 40 })
    ScrollTrigger.create({
      trigger: '#stats', start: 'top 82%', once: true,
      onEnter: () => gsap.to('.stat', { opacity: 1, y: 0, duration: 0.9, ease: 'power3.out', stagger: 0.12 }),
    })

    /* eyebrow ticks draw out */
    q('.eyebrow .tick').forEach((t) => {
      ScrollTrigger.create({
        trigger: t, start: 'top 88%', once: true,
        onEnter: () => gsap.to(t, { width: 28, duration: 0.8, ease: 'power2.out' }),
      })
    })

    /* wax seal unseals on scroll (scrubbed) */
    gsap.set('.sreveal', { opacity: 0.14 })
    gsap.timeline({ scrollTrigger: { trigger: '#verses .stage', start: 'top 74%', end: 'top 30%', scrub: 0.7 } })
      .to('#bigseal', { y: -84, rotate: -22, scale: 0.62, opacity: 0, ease: 'power2.in' })
      .to('.sreveal', { opacity: 1, ease: 'power2.out' }, '-=.35')

    /* shield draws itself */
    ScrollTrigger.create({
      trigger: '#safety', start: 'top 66%', once: true,
      onEnter: () => gsap.to('.shield .draw', { strokeDashoffset: 0, duration: 1.6, ease: 'power1.inOut', stagger: 0.5 }),
    })

    /* stats count up */
    q('[data-count]').forEach((node) => {
      const end = +node.dataset.count
      ScrollTrigger.create({
        trigger: node, start: 'top 88%', once: true,
        onEnter: () => {
          const obj = { v: 0 }
          gsap.to(obj, { v: end, duration: 1.6, ease: 'power2.out', onUpdate: () => { node.innerText = Math.round(obj.v) } })
        },
      })
    })

    /* micro-interactions: magnetic buttons + card tilt */
    if (matchMedia('(pointer:fine)').matches) {
      q('[data-magnetic]').forEach((m) => {
        const move = (e) => {
          const r = m.getBoundingClientRect()
          const dx = (e.clientX - r.left - r.width / 2) / r.width
          const dy = (e.clientY - r.top - r.height / 2) / r.height
          m.style.transform = `translate(${dx * 8}px, ${dy * 6}px)`
        }
        const leave = () => {
          m.style.transition = 'transform .5s cubic-bezier(.22,.61,.30,1)'
          m.style.transform = ''
          setTimeout(() => { m.style.transition = '' }, 500)
        }
        m.addEventListener('mousemove', move)
        m.addEventListener('mouseleave', leave)
        cleanups.push(() => { m.removeEventListener('mousemove', move); m.removeEventListener('mouseleave', leave) })
      })

      q('[data-tilt]').forEach((c) => {
        const move = (e) => {
          const r = c.getBoundingClientRect()
          const dx = (e.clientX - r.left) / r.width - 0.5
          const dy = (e.clientY - r.top) / r.height - 0.5
          c.style.transform = `perspective(900px) rotateY(${dx * 4}deg) rotateX(${-dy * 4}deg)`
        }
        const leave = () => {
          c.style.transition = 'transform .6s cubic-bezier(.22,.61,.30,1)'
          c.style.transform = 'perspective(900px) rotateY(0deg) rotateX(0deg)'
          setTimeout(() => { c.style.transition = '' }, 600)
        }
        c.addEventListener('mousemove', move)
        c.addEventListener('mouseleave', leave)
        cleanups.push(() => { c.removeEventListener('mousemove', move); c.removeEventListener('mouseleave', leave) })
      })
    }

    return () => cleanups.forEach((fn) => fn && fn())
  }, { scope: root })

  return (
    <div ref={root}>
      {/* ambient aurora — drifting multi-tone washes of cream behind everything */}
      <div className="aurora" aria-hidden="true"><i /><i /><i /><i /></div>
      {/* illuminated-manuscript frame — the toile ornaments stay fixed at the
          viewport edges while the acts scroll through the empty centre */}
      <div className="page-frame" aria-hidden="true">
        <i className="pf pf-l" /><i className="pf pf-r" />
      </div>
      <div className="grain" aria-hidden="true" />

      {/* shared SVG defs */}
      <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true">
        <defs>
          <radialGradient id="sealGrad" cx="36%" cy="30%" r="80%">
            <stop offset="0" stopColor="#c8825f" />
            <stop offset="46%" stopColor="#a65b43" />
            <stop offset="100%" stopColor="#6f3626" />
          </radialGradient>
        </defs>
      </svg>

      <Nav />
      <main>
        {/* Stage 1: Static hero — fills viewport, completely still */}
        <Hero />

        {/* Stage 2 pause: a manuscript chapter-break bridges the dissolved hero
            into the content — a shaft of light descends into a wax seal */}
        <div className="hero-pause" aria-hidden="true">
          <div className="pause-inner">
            <span className="pause-beam" />
            <span className="pause-seal">†</span>
            <div className="pause-rule"><i /><span>Scripture, continued</span><i /></div>
          </div>
        </div>

        {/* Stage 3: Progressive content reveal — each element scrolls in */}
        <Marquee />
        <Features />
        <Stats />
        <Footer />
      </main>
    </div>
  )
}
