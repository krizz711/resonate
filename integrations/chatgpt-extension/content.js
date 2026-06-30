// Resonate content script for chatgpt.com.
// Watches for new USER messages (the stable [data-message-author-role="user"] selector),
// sends the text to the background worker -> local engine, and renders a quiet, dismissible
// side panel. If the selector ever fails or the engine is offline, it does nothing — it never
// touches or breaks the chat UI.

(function () {
  const USER_ID = "chat_" + Math.random().toString(36).slice(2, 10); // per-tab session, not stored
  let lastText = "";
  let debounce = null;
  let host = null;
  let shadow = null;
  let card = null;

  const PANEL_CSS = `
    .card{width:300px;font-family:-apple-system,Segoe UI,Roboto,sans-serif;
      background:linear-gradient(180deg,#161b27,#10141d);color:#ece3d0;border:1px solid #2a3349;
      border-left:3px solid #caa84e;border-radius:14px;padding:16px 16px 12px;
      box-shadow:0 12px 40px rgba(0,0,0,.45);position:relative;animation:rin .25s ease}
    .card.hidden{display:none}
    @keyframes rin{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
    .x{position:absolute;top:7px;right:10px;background:none;border:none;color:#6b7793;
      font-size:18px;cursor:pointer;line-height:1}
    .x:hover{color:#ece3d0}
    .ref{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#caa84e;
      margin-bottom:8px;padding-right:18px}
    .ref .tr{color:#6b7793}
    .verse{font-family:"Iowan Old Style",Palatino,Georgia,serif;font-size:15.5px;line-height:1.5;color:#f3ecdb}
    .bridge{margin-top:10px;font-size:13px;font-style:italic;color:#9aa6bd;
      border-top:1px dashed #2a3349;padding-top:9px}
    .foot{margin-top:10px;font-size:10.5px;color:#5d6680}
    .card.help{border-left-color:#e0a35a}
    .card.help .ref{color:#e0a35a}`;

  function ensurePanel() {
    if (host) return;
    host = document.createElement("div");
    host.style.cssText = "position:fixed;right:18px;bottom:96px;z-index:2147483647;";
    shadow = host.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = PANEL_CSS;
    card = document.createElement("div");
    card.className = "card hidden";
    shadow.append(style, card);
    document.documentElement.appendChild(host);
  }

  function esc(s) {
    return (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  }

  function showVerse(d) {
    ensurePanel();
    card.className = "card verse";
    card.innerHTML =
      '<button class="x" title="Dismiss">×</button>' +
      '<div class="ref">' + esc(d.reference) + ' <span class="tr">' + esc(d.translation) + "</span></div>" +
      '<div class="verse">' + esc(d.verse_text) + "</div>" +
      '<div class="bridge">' + esc(d.bridge) + "</div>" +
      '<div class="foot">Resonate · processed locally · nothing stored</div>';
    card.querySelector(".x").onclick = () => card.classList.add("hidden");
  }

  function showHelp(message) {
    ensurePanel();
    card.className = "card help";
    card.innerHTML =
      '<button class="x" title="Dismiss">×</button>' +
      '<div class="ref">A pause, not a verse</div>' +
      '<div class="verse">' + esc(message) + "</div>" +
      '<div class="foot">Resonate · your wellbeing comes first</div>';
    card.querySelector(".x").onclick = () => card.classList.add("hidden");
  }

  function handle(text) {
    if (!text || text === lastText) return;
    lastText = text;
    try {
      chrome.runtime.sendMessage({ type: "resonate", text, userId: USER_ID }, (resp) => {
        if (chrome.runtime.lastError || !resp || !resp.ok) return; // engine offline -> stay invisible
        const data = resp.data || {};
        const policy = data.policy || {};
        const deliveries = data.deliveries || [];
        if (policy.safety) {
          const hold = deliveries.find((d) => d.status === "safety_hold");
          if (hold) showHelp(hold.message);
          return;
        }
        if (policy.surface) {
          const d = deliveries.find((x) => x.status === "delivered");
          if (d) showVerse(d);
        }
        // otherwise: stay silent — the whole point.
      });
    } catch (e) {
      /* extension context invalidated (e.g. reloaded) — ignore */
    }
  }

  function latestUserMessage() {
    const nodes = document.querySelectorAll('[data-message-author-role="user"]');
    if (!nodes.length) return "";
    return (nodes[nodes.length - 1].innerText || "").trim();
  }

  const observer = new MutationObserver(() => {
    clearTimeout(debounce);
    debounce = setTimeout(() => handle(latestUserMessage()), 600);
  });

  function start() {
    observer.observe(document.body, { childList: true, subtree: true });
  }
  if (document.body) start();
  else window.addEventListener("DOMContentLoaded", start);
})();
