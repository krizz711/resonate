import Lenis from 'lenis'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

/**
 * Wire Lenis smooth-scroll to GSAP's ticker and keep ScrollTrigger in sync.
 * Returns a cleanup function.
 */
export function initSmoothScroll() {
  const lenis = new Lenis({ lerp: 0.09, wheelMultiplier: 0.92, smoothWheel: true })
  lenis.on('scroll', ScrollTrigger.update)

  const onTick = (time) => lenis.raf(time * 1000)
  gsap.ticker.add(onTick)
  gsap.ticker.lagSmoothing(0)

  return () => {
    gsap.ticker.remove(onTick)
    lenis.destroy()
  }
}
