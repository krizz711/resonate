// Background service worker — the only place that talks to the Resonate engine.
// Content scripts can't fetch the engine directly (the page's CSP blocks it), but the
// worker can (granted via host_permissions). It stays invisible if no engine answers.
//
// Two engines, resolved once per worker life:
//   • a LOCAL engine (python scripts/serve.py) — full Kokoro voices, for development;
//   • the HOSTED engine on Render — so the extension works with zero setup (no Plus, no
//     Python). Free-plan ChatGPT users, who can't add a custom MCP connector, use this path.
// We prefer local when it's actually running, otherwise fall back to hosted.

const LOCAL = "http://127.0.0.1:8765";
const HOSTED = "https://resonate-hg6j.onrender.com"; // change if the Render URL changes

// Resolve the engine base once and memoize. A local /health probe fails fast (connection
// refused) when no local engine is up, so end users pay ~no latency before hosted wins.
let _basePromise = null;
function resolveBase() {
  if (!_basePromise) {
    _basePromise = (async () => {
      try {
        const ctrl = new AbortController();
        const t = setTimeout(() => ctrl.abort(), 600);
        const r = await fetch(LOCAL + "/health", { signal: ctrl.signal });
        clearTimeout(t);
        if (r.ok) return LOCAL;
      } catch (e) { /* no local engine running — use the hosted one */ }
      return HOSTED;
    })();
  }
  return _basePromise;
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "base") {
    // content.js asks which engine won, so its "Ask Ezra" link opens the SAME server
    // that received the hand-off (local and hosted must not be crossed mid-flow).
    resolveBase().then((base) => sendResponse({ ok: true, base }));
    return true;
  }

  if (msg && msg.type === "resonate") {
    resolveBase().then((BASE) =>
      fetch(BASE + "/resonate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: msg.text,
          user_id: msg.userId,
          event: "message",
          history: msg.history || [], // recent prior messages — conversation-aware verse choice
        }),
      })
        .then((r) => r.json())
        .then((data) => sendResponse({ ok: true, data }))
    ).catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true; // keep the message channel open for the async response
  }

  if (msg && msg.type === "story") {
    resolveBase().then((BASE) =>
      fetch(BASE + "/story", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: msg.userId, text: msg.text, beat: msg.beat,
          verse: msg.verse, memory_note: msg.memoryNote,
        }),
      })
        .then((r) => r.json())
        .then((data) => sendResponse({ ok: true, data }))
    ).catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }

  if (msg && msg.type === "voices") {
    // the engine's /voices is the single source of truth for the Kokoro list —
    // the panel only falls back to its built-in defaults when the engine is away
    resolveBase().then((BASE) =>
      fetch(BASE + "/voices")
        .then((r) => r.json())
        .then((data) => sendResponse({ ok: true, data }))
    ).catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }

  if (msg && msg.type === "handoff") {
    // "Ask Ezra about this" — park the moment engine-side (single-read, short TTL) so
    // the guide page can pick it up without the words ever riding in a URL.
    resolveBase().then((BASE) =>
      fetch(BASE + "/handoff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: msg.userId, text: msg.text }),
      })
    ).catch(() => {});
    return false; // fire-and-forget
  }

  if (msg && msg.type === "tts") {
    // Fetch the Kokoro voice as bytes and hand them to the content script as base64
    // (messages must be JSON-serializable). 503 => tell the panel to use Web Speech.
    resolveBase().then((BASE) =>
      fetch(BASE + "/tts?voice=" + encodeURIComponent(msg.voice || "bella") +
            "&text=" + encodeURIComponent(msg.text || ""))
        .then(async (r) => {
          if (!r.ok) { sendResponse({ ok: false, fallback: true }); return; }
          const buf = await r.arrayBuffer();
          let bin = "";
          const bytes = new Uint8Array(buf);
          const CHUNK = 0x8000;
          for (let i = 0; i < bytes.length; i += CHUNK)
            bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
          sendResponse({ ok: true, b64: btoa(bin), mime: "audio/wav" });
        })
    ).catch(() => sendResponse({ ok: false, fallback: true }));
    return true;
  }
});
