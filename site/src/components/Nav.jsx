import { useEffect, useState } from 'react'

export default function Nav() {
  const [solid, setSolid] = useState(false)

  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 70)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header className={`nav${solid ? ' solid' : ''}`} id="nav">
      <ul>
        <li><a href="#hero">The Aim</a></li>
        <li><a href="#features">Features</a></li>
        <li><a href="#voices">Voices</a></li>
        <li><a href="#mcp">MCP</a></li>
      </ul>
      <a className="docs" href="https://github.com/krizz711/resonate" target="_blank" rel="noopener">Docs ↗</a>
    </header>
  )
}
