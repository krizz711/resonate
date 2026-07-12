import { Suspense, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Canvas, useFrame, useThree, advance } from '@react-three/fiber'
import { useGLTF } from '@react-three/drei'
import * as THREE from 'three'
import { computeBoundsTree, disposeBoundsTree, acceleratedRaycast } from 'three-mesh-bvh'

// BVH-accelerated raycasts: the statue is ~12 MB of triangles, and the silver
// hover-reveal raycasts on every pointer move — brute force would melt the frame.
THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree
THREE.BufferGeometry.prototype.disposeBoundsTree = disposeBoundsTree
THREE.Mesh.prototype.raycast = acceleratedRaycast

function Christus() {
  const { scene } = useGLTF('/christus_plain.glb')
  const group = useRef()
  const range = useRef({ min: -1, max: 1 })
  // silver reveal: BVH built lazily after load; handlers attach only once ready
  const [ready, setReady] = useState(false)
  const hover = useRef({ active: false, target: new THREE.Vector3(0, 0, 9999) })
  // shared uniforms: the rising gold band + the silver hover reveal
  const u = useRef({
    uBandY: { value: 0 },
    uColor: { value: new THREE.Color('#ffe7b3') },
    uWidth: { value: 0.085 },
    uStrength: { value: 2.4 },
    // where the cursor touches the figure, the cream gives way to silver —
    // a soft-edged patch with a cool blue sheen ring at its rim
    uHoverPos: { value: new THREE.Vector3(0, 0, 9999) },
    uHoverStrength: { value: 0 },
    uHoverRadius: { value: 0.42 },
    uSilver: { value: new THREE.Color('#ccd4e0') },
    uSheen: { value: new THREE.Color('#8ab4ff') },
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
          uHoverPos: u.current.uHoverPos,
          uHoverStrength: u.current.uHoverStrength,
          uHoverRadius: u.current.uHoverRadius,
          uSilver: u.current.uSilver,
          uSheen: u.current.uSheen,
        })
        sh.vertexShader = 'varying float vObjY;\nvarying vec3 vWorldPos;\n' + sh.vertexShader.replace(
          '#include <begin_vertex>',
          '#include <begin_vertex>\n  vObjY = position.y;\n  vWorldPos = (modelMatrix * vec4(transformed, 1.0)).xyz;'
        )
        sh.fragmentShader =
          'uniform float uBandY; uniform vec3 uColor; uniform float uWidth; uniform float uStrength;\n' +
          'uniform vec3 uHoverPos; uniform float uHoverStrength; uniform float uHoverRadius;\n' +
          'uniform vec3 uSilver; uniform vec3 uSheen;\n' +
          'varying float vObjY; varying vec3 vWorldPos;\n' +
          sh.fragmentShader
            // the mask is declared here (first include in main) so the roughness,
            // metalness and emissive stages below can all reuse it.
            // Gaussian falloff: fully silver AT the cursor, dimming continuously
            // with distance — no plateau, no edge, no visible circle.
            .replace(
              '#include <color_fragment>',
              '#include <color_fragment>\n' +
              '  float _hd = distance(vWorldPos, uHoverPos) / uHoverRadius;\n' +
              '  float _hMask = exp(-2.2 * _hd * _hd) * uHoverStrength;\n' +
              '  diffuseColor.rgb = mix(diffuseColor.rgb, uSilver, _hMask);'
            )
            .replace(
              '#include <roughnessmap_fragment>',
              '#include <roughnessmap_fragment>\n  roughnessFactor = mix(roughnessFactor, 0.16, _hMask);'
            )
            .replace(
              '#include <metalnessmap_fragment>',
              '#include <metalnessmap_fragment>\n  metalnessFactor = mix(metalnessFactor, 0.85, _hMask);'
            )
            .replace(
              '#include <emissivemap_fragment>',
              '#include <emissivemap_fragment>\n' +
              // gold band — cooled to near-nothing inside the silver patch
              '  float _d=(vObjY-uBandY)/uWidth; totalEmissiveRadiance += uColor*exp(-_d*_d)*uStrength*(1.0 - _hMask*0.9);\n' +
              // faint cool fill so the metal reads as lit chrome, not a hole — it rides
              // the same gaussian mask, so it dims with distance and draws no outline
              '  totalEmissiveRadiance += mix(uSilver, uSheen, 0.35) * 0.10 * _hMask;'
            )
      }
      m.needsUpdate = true
    })
    range.current = { min: gy0, max: gy1 }

    // centre + scale to a fixed height (bigger than before)
    const box = new THREE.Box3().setFromObject(scene)
    const c = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const targetHeight = 2.02;
    const s = targetHeight / size.y;
    const bottomY = -0.974; // Approx bottom of camera frustum at z=0
    const centerY = bottomY + (targetHeight / 2);

    const g = group.current
    g.scale.setScalar(s)
    g.position.set(-c.x * s, (-c.y * s) + centerY, -c.z * s)
  }, [scene])

  useEffect(() => {
    // Build the BVH after the intro settles — a one-time main-thread task; until
    // it exists the reveal handlers stay detached so no slow raycast can run.
    let cancelled = false
    const t = setTimeout(() => {
      if (cancelled) return
      scene.traverse((o) => {
        if (o.isMesh && !o.geometry.boundsTree) o.geometry.computeBoundsTree()
      })
      if (!cancelled) setReady(true)
    }, 1500)
    return () => { cancelled = true; clearTimeout(t) }
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

    // — silver reveal: the patch glides after the cursor and breathes gently —
    const h = hover.current
    const targetS = h.active && ready ? 1 : 0
    uu.uHoverStrength.value += (targetS - uu.uHoverStrength.value) * Math.min(1, dt * 6)
    uu.uHoverPos.value.lerp(h.target, Math.min(1, dt * 11))
    uu.uHoverRadius.value = 0.42 * (1 + 0.045 * Math.sin(state.clock.elapsedTime * 2.1))
    if (typeof window !== 'undefined' && window.__silverDebug) {
      window.__silverState = {
        strength: +uu.uHoverStrength.value.toFixed(3),
        pos: uu.uHoverPos.value.toArray().map((v) => +v.toFixed(3)),
        ready,
      }
    }

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
    // brightness envelope — the band stays full for most of the climb and only
    // dips to zero briefly at the base and crown, so the loop's wrap-around
    // happens while it's invisible (a smooth fade, never a hard snap-reset)
    const FADE = 0.1
    let env = raw < FADE ? raw / FADE : raw > 1 - FADE ? (1 - raw) / FADE : 1
    env = env * env * (3 - 2 * env) // smoothstep
    uu.uStrength.value = 2.4 * env
  })

  const revealHandlers = ready
    ? {
        onPointerMove: (e) => {
          if (e.pointerType === 'touch') return // hover is a mouse idea
          hover.current.active = true
          hover.current.target.copy(e.point)
        },
        onPointerOut: () => { hover.current.active = false },
      }
    : {}

  return (
    <group ref={group}>
      <primitive object={scene} {...revealHandlers} />
    </group>
  )
}

export default function HeroStatue3D() {
  const wrap = useRef(null)
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

  return (
    <div className="hero-3d" ref={wrap}>
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
          <Christus />
        </Suspense>
      </Canvas>
    </div>
  )
}

useGLTF.preload('/christus_plain.glb')
