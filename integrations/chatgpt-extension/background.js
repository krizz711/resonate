// Background service worker — the only place that talks to the local engine.
// Content scripts can't fetch localhost (the page's CSP blocks it), but the worker can
// (granted via host_permissions). It stays invisible if the engine isn't running.

const ENGINE = "http://127.0.0.1:8765/resonate";

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "resonate") {
    fetch(ENGINE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: msg.text, user_id: msg.userId, event: "message" }),
    })
      .then((r) => r.json())
      .then((data) => sendResponse({ ok: true, data }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true; // keep the message channel open for the async response
  }
});
