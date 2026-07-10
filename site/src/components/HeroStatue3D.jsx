import { Suspense, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { useGLTF } from '@react-three/drei'
import * as THREE from 'three'

function Christus() {
  const { scene } = useGLTF('/christus_plain.glb')
  const group = useRef()
  const range = useRef({ min: -1, max: 1 })
  // shared uniforms for the rising-light band
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
        sh.uniforms.uBandY = u.current.uBandY
        sh.uniforms.uColor = u.current.uColor
        sh.uniforms.uWidth = u.current.uWidth
        sh.uniforms.uStrength = u.current.uStrength
        sh.vertexShader = 'varying float vObjY;\n' + sh.vertexShader.replace(
          '#include <begin_vertex>',
          '#include <begin_vertex>\n  vObjY = position.y;'
        )
        sh.fragmentShader =
          'uniform float uBandY; uniform vec3 uColor; uniform float uWidth; uniform float uStrength; varying float vObjY;\n' +
          sh.fragmentShader.replace(
            '#include <emissivemap_fragment>',
            '#include <emissivemap_fragment>\n  float _d=(vObjY-uBandY)/uWidth; totalEmissiveRadiance += uColor*exp(-_d*_d)*uStrength;'
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

  useFrame((state) => {
    const { min, max } = range.current
    // debug freeze hook: window.__bandP in [0,1]
    if (typeof window !== 'undefined' && window.__bandP != null) {
      u.current.uBandY.value = min + (max - min) * window.__bandP
      u.current.uStrength.value = 2.4
      return
    }
    const dur = 6.0
    const raw = (state.clock.elapsedTime % dur) / dur // 0→1 sawtooth
    // eased vertical position — soft start/stop as it climbs the figure
    const p = raw < 0.5 ? 2 * raw * raw : 1 - Math.pow(-2 * raw + 2, 2) / 2
    u.current.uBandY.value = min + (max - min) * p
    // brightness envelope — the band stays full for most of the climb and only
    // dips to zero briefly at the base and crown, so the loop's wrap-around
    // happens while it's invisible (a smooth fade, never a hard snap-reset)
    const FADE = 0.1
    let env = raw < FADE ? raw / FADE : raw > 1 - FADE ? (1 - raw) / FADE : 1
    env = env * env * (3 - 2 * env) // smoothstep
    u.current.uStrength.value = 2.4 * env
  })

  return (
    <group ref={group}>
      <primitive object={scene} />
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
