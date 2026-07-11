import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The marketing site (this Vite app) and the live surfaces (Ezra chat/call at
// /guide.html, Reels at /reels.html, and their JSON APIs) are one product but two
// processes: Vite here on 5173, the Python engine on 8765. In dev we proxy the
// engine's routes so http://localhost:5173 is a single working origin — the nav's
// "Reels"/"Ezra" links and every fetch to /guide, /reel-groups, /tts just work.
// (In production the engine serves the built site from site/dist, so no proxy needed.)
const ENGINE = 'http://127.0.0.1:8765'
const engineRoutes = [
  '/guide',       // POST /guide  +  GET /guide.html
  '/reels.html',
  '/reel-groups',
  '/resonate',
  '/story',
  '/tts',
  '/voices',
  '/health',
  '/ext',         // /ext/content.js (extension script, for the mock chat)
  '/bg',          // /bg/athena.jpg — the standalone pages' background art (in web/)
]

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 5173,
    host: true,
    open: false,
    proxy: Object.fromEntries(engineRoutes.map((r) => [r, { target: ENGINE, changeOrigin: true }])),
  },
})
