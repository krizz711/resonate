import { Suspense, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Canvas, useFrame, useThree, advance } from '@react-three/fiber'
import { useGLTF } from '@react-three/drei'
import * as THREE from 'three'

function Christus({ pointer }) {
  const { scene } = useGLTF('/christus_plain.glb')
  const group = useRef()
  const range = useRef({ min: -1, max: 1 })
  const baseScale = useRef(1)
  const hoverAmt = useRef(0) // eased 0→1 hover presence, drives the micro-movement
  // rising gold band uniforms (kept — only the silver hover-reveal was removed)
  const u = useRef({
    uBandY: { value: 0 },
    uColor: { value: new THREE.Color('#ffe7b3') },
    uWidth: { value: 0.085 },
    uStrength: { value: 2.4 },
  })

  useLayoutEffect(() => {
    // face front (native mesh looks along +X)
    scene.rotation.set(0, -Math.PI / 2, 0)
    scene.updateMatrixWorld(true)

    let gy0 = Infinity, gy1 = -Infinity
    scene.traverse((o) => {
      if (!o.isMesh) return
      o.frustumCulled = false
      o.geometry.computeBoundingBox()
      gy0 = Math.min(gy0, o.geometry.boundingBox.min.y)
      gy1 = Math.max(gy1, o.geometry.boundingBox.max.y)
      const m = o.material
      m.color.set('#e9e3d7')
      m.roughness = 0.5
      m.metalness = 0.0
      m.map = null
      m.envMapIntensity = 0.7
      m.onBeforeCompile = (sh) => {
        Object.assign(sh.uniforms, {
          uBandY: u.current.uBandY,
          uColor: u.current.uColor,
          uWidth: u.current.uWidth,
          uStrength: u.current.uStrength,
        })
        sh.vertexShader = 'varying float vObjY;\n' + sh.vertexShader.replace(
          '#include <begin_vertex>',
          '#include <begin_vertex>\n  vObjY = position.y;'
        )
        // a single warm band of light that climbs the figure and loops — nothing else
        sh.fragmentShader =
          'uniform float uBandY; uniform vec3 uColor; uniform float uWidth; uniform float uStrength;\n' +
          'varying float vObjY;\n' +
          sh.fragmentShader.replace(
            '#include <emissivemap_fragment>',
            '#include <emissivemap_fragment>\n' +
            '  float _d=(vObjY-uBandY)/uWidth; totalEmissiveRadiance += uColor*exp(-_d*_d)*uStrength;'
          )
      }
      m.needsUpdate = true
    })
    range.current = { min: gy0, max: gy1 }

    // centre + scale to a fixed height
    const box = new THREE.Box3().setFromObject(scene)
    const c = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const targetHeight = 2.02
    const s = targetHeight / size.y
    const bottomY = -0.974 // approx bottom of camera frustum at z=0
    const centerY = bottomY + (targetHeight / 2)

    const g = group.current
    g.scale.setScalar(s)
    g.position.set(-c.x * s, (-c.y * s) + centerY, -c.z * s)
    baseScale.current = s
  }, [scene])

  // headless-verification hook: environments without requestAnimationFrame (the
  // preview harness) can size the canvas and pump frames by hand
  const getThree = useThree((s) => s.get)
  useEffect(() => {
    if (typeof window === 'undefined') return
    window.__resonate3d = { get: getThree, advance: (t) => advance(t) }
    return () => { delete window.__resonate3d }
  }, [getThree])

  useFrame((state, delta) => {
    const uu = u.current
    const dt = Math.min(delta || 0.016, 0.05)
    const g = group.current
    if (!g) return

    // — micro-movement on hover: a gentle parallax tilt toward the cursor plus a
    //   hair of lift; it eases back to rest when the pointer leaves. Kept tiny on
    //   purpose — the figure should feel alive, not animated. —
    const pt = (pointer && pointer.current) || { x: 0, y: 0, h: false }
    hoverAmt.current += ((pt.h ? 1 : 0) - hoverAmt.current) * Math.min(1, dt * 5)
    const ha = hoverAmt.current
    const k = Math.min(1, dt * 6)
    const tRotY = pt.x * 0.055 * ha      // look slightly toward the cursor's x
    const tRotX = pt.y * 0.04 * ha       // and nod a touch with its y
    g.rotation.y += (tRotY - g.rotation.y) * k
    g.rotation.x += (tRotX - g.rotation.x) * k
    const tS = baseScale.current * (1 + 0.025 * ha)   // ~2.5% lift on hover
    g.scale.setScalar(g.scale.x + (tS - g.scale.x) * k)

    // — rising gold band (kept) —
    const { min, max } = range.current
    // debug freeze hook: window.__bandP in [0,1]
    if (typeof window !== 'undefined' && window.__bandP != null) {
      uu.uBandY.value = min + (max - min) * window.__bandP
      uu.uStrength.value = 2.4
      return
    }
    const dur = 6.0
    const raw = (state.clock.elapsedTime % dur) / dur // 0→1 sawtooth
    // eased vertical position — soft start/stop as it climbs the figure
    const p = raw < 0.5 ? 2 * raw * raw : 1 - Math.pow(-2 * raw + 2, 2) / 2
    uu.uBandY.value = min + (max - min) * p
    // brightness envelope — full for most of the climb, fading to zero only at the
    // base and crown so the loop wraps while invisible (a fade, never a hard reset)
    const FADE = 0.1
    let env = raw < FADE ? raw / FADE : raw > 1 - FADE ? (1 - raw) / FADE : 1
    env = env * env * (3 - 2 * env) // smoothstep
    uu.uStrength.value = 2.4 * env
  })

  return (
    <group ref={group}>
      <primitive object={scene} />
    </group>
  )
}

export default function HeroStatue3D() {
  const wrap = useRef(null)
  const pointer = useRef({ x: 0, y: 0, h: false })
  // Only render the WebGL scene while the hero is on screen — once it scrolls
  // away, pause the render loop so the rest of the page scrolls at full frame.
  const [active, setActive] = useState(true)
  useEffect(() => {
    const el = wrap.current
    if (!el || typeof IntersectionObserver === 'undefined') return
    const io = new IntersectionObserver(
      ([e]) => setActive(e.isIntersecting),
      { rootMargin: '160px' }
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  // Track the cursor within the hero as normalized -1..1 so the figure can lean
  // toward it. DOM-level (no mesh raycasting) — cheap, and it reads the whole
  // hero area so the movement feels continuous, never snapping at the silhouette.
  const onMove = (e) => {
    const el = wrap.current
    if (!el) return
    const r = el.getBoundingClientRect()
    pointer.current.x = ((e.clientX - r.left) / r.width) * 2 - 1
    pointer.current.y = ((e.clientY - r.top) / r.height) * 2 - 1
  }

  return (
    <div
      className="hero-3d"
      ref={wrap}
      onPointerMove={onMove}
      onPointerEnter={() => { pointer.current.h = true }}
      onPointerLeave={() => { pointer.current.h = false }}
    >
      <Canvas
        frameloop={active ? 'always' : 'never'}
        camera={{ position: [0, 0.05, 3.35], fov: 34 }}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        dpr={[1, 1.5]}
      >
        <hemisphereLight args={['#fff6e6', '#cdbfa6', 0.9]} />
        <ambientLight intensity={0.32} />
        <directionalLight position={[-3.5, 4, 4]} intensity={1.5} color="#fff3da" />
        <directionalLight position={[3.5, 1.2, 2.5]} intensity={0.55} color="#eef4ff" />
        <directionalLight position={[0, 2.5, -4]} intensity={0.9} color="#ffd9a0" />
        <Suspense fallback={null}>
          <Christus pointer={pointer} />
        </Suspense>
      </Canvas>
    </div>
  )
}

useGLTF.preload('/christus_plain.glb')
