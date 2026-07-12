// Background service worker — the only place that talks to the local engine.
// Content scripts can't fetch localhost (the page's CSP blocks it), but the worker can
// (granted via host_permissions). It stays invisible if the engine isn't running.

const BASE = "http://127.0.0.1:8765";

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "resonate") {
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
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true; // keep the message channel open for the async response
  }

  if (msg && msg.type === "story") {
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
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }

  if (msg && msg.type === "handoff") {
    // "Ask Ezra about this" — park the moment engine-side (single-read, short TTL) so
    // the guide page can pick it up without the words ever riding in a URL.
    fetch(BASE + "/handoff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: msg.userId, text: msg.text }),
    }).catch(() => {});
    return false; // fire-and-forget
  }

  if (msg && msg.type === "tts") {
    // Fetch the Kokoro voice as bytes and hand them to the content script as base64
    // (messages must be JSON-serializable). 503 => tell the panel to use Web Speech.
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
      .catch(() => sendResponse({ ok: false, fallback: true }));
    return true;
  }
});
