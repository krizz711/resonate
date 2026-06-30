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

  // --- voice (opt-in, click-to-play; auto-read is OFF by default and remembered) ---
  let autoSpeak = false;
  try { window.speechSynthesis.getVoices(); window.speechSynthesis.onvoiceschanged = () => {}; } catch (e) {}
  try {
    if (chrome.storage && chrome.storage.sync)
      chrome.storage.sync.get({ autoSpeak: false }, (r) => { autoSpeak = !!r.autoSpeak; });
  } catch (e) {}

  function pickVoice() {
    let vs = [];
    try { vs = window.speechSynthesis.getVoices() || []; } catch (e) {}
    const prefer = ["Google UK English Female", "Microsoft Aria", "Microsoft Sonia", "Microsoft Jenny",
                    "Samantha", "Microsoft Zira", "Google US English", "Daniel"];
    for (const name of prefer) { const m = vs.find((v) => v.name && v.name.includes(name)); if (m) return m; }
    return vs.find((v) => /^en/i.test(v.lang || "")) || vs[0] || null;
  }
  function speak(text) {
    try {
      const synth = window.speechSynthesis; if (!synth) return;
      synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      const v = pickVoice(); if (v) u.voice = v;
      u.rate = 0.92; u.pitch = 0.96; u.volume = 1;  // warm, unhurried, reverent
      u.onend = () => { const b = card && card.querySelector(".listen"); if (b) b.textContent = "▸ Listen"; };
      synth.speak(u);
    } catch (e) {}
  }
  function stopSpeak() { try { window.speechSynthesis.cancel(); } catch (e) {} }

  // Parchment / aged-manuscript skin (matches the portfolio: paper #efe9df, ink #211d17,
  // clay #a65b43). Kept in sync with web/panel-preview.html.
  const PANEL_CSS = `
    .card{width:370px;box-sizing:border-box;
      font-family:'Space Grotesk',ui-sans-serif,-apple-system,'Segoe UI',Roboto,sans-serif;color:#211d17;
      background:radial-gradient(130% 120% at 100% 0%, rgba(166,91,67,.07), transparent 58%),
        linear-gradient(177deg,#efe9df 0%,#e9e1d3 58%,#e3d7c4 100%);
      border:1px solid rgba(33,29,23,.22);border-radius:18px;padding:22px 24px 15px;
      box-shadow:0 18px 50px rgba(33,29,23,.28), inset 0 1px 0 rgba(255,255,255,.5);
      position:relative;animation:rin .32s cubic-bezier(.22,.61,.36,1)}
    .card.hidden{display:none}
    .card::before{content:"";position:absolute;inset:7px;border:1px solid rgba(33,29,23,.13);
      border-radius:12px;pointer-events:none}
    @keyframes rin{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
    .x{position:absolute;top:10px;right:13px;background:none;border:none;color:#9a8f7f;font-size:17px;
      cursor:pointer;line-height:1;font-family:inherit;z-index:1}
    .x:hover{color:#a65b43}
    .ref{font-size:11px;letter-spacing:.3em;text-transform:uppercase;color:#a65b43;margin:0 0 11px;padding-right:18px}
    .ref .tr{color:#a89c8a;letter-spacing:.2em}
    .ref::after{content:"";display:block;width:32px;height:1px;background:#a65b43;opacity:.55;margin-top:9px}
    .verse{font-family:'Cormorant Garamond','EB Garamond','Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif;
      font-size:22px;line-height:1.4;color:#211d17;font-weight:500}
    .bridge{margin-top:13px;font-family:'Cormorant Garamond','EB Garamond',Georgia,serif;font-size:15px;
      font-style:italic;color:#6b6358;border-top:1px solid rgba(33,29,23,.13);padding-top:11px}
    .foot{margin-top:13px;font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:#a89c8a}
    .card.help .verse{font-size:17.5px}
    .card.help .ref::after{width:46px}
    .row{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:14px}
    .listen{font-family:inherit;font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:#a65b43;
      background:none;border:1px solid rgba(166,91,67,.45);border-radius:999px;padding:5px 13px;cursor:pointer}
    .listen:hover{background:rgba(166,91,67,.10)}
    .auto{font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:#a89c8a;cursor:pointer;user-select:none}
    .auto b{color:#6b6358}`;

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
    stopSpeak();
    card.className = "card verse";
    card.innerHTML =
      '<button class="x" title="Dismiss">×</button>' +
      '<div class="ref">' + esc(d.reference) + ' <span class="tr">' + esc(d.translation) + "</span></div>" +
      '<div class="verse">' + esc(d.verse_text) + "</div>" +
      '<div class="bridge">' + esc(d.bridge) + "</div>" +
      '<div class="row">' +
        '<button class="listen">▸ Listen</button>' +
        '<span class="auto" title="Read every verse aloud automatically">auto-read: <b>' + (autoSpeak ? "on" : "off") + "</b></span>" +
      "</div>" +
      '<div class="foot">Resonate · processed locally · nothing stored</div>';

    const listenBtn = card.querySelector(".listen");
    listenBtn.onclick = () => {
      if (window.speechSynthesis && window.speechSynthesis.speaking) { stopSpeak(); listenBtn.textContent = "▸ Listen"; }
      else { speak(d.verse_text); listenBtn.textContent = "■ Stop"; }
    };
    card.querySelector(".auto").onclick = (e) => {
      autoSpeak = !autoSpeak;
      e.currentTarget.querySelector("b").textContent = autoSpeak ? "on" : "off";
      try { if (chrome.storage && chrome.storage.sync) chrome.storage.sync.set({ autoSpeak }); } catch (err) {}
      if (autoSpeak) { speak(d.verse_text); listenBtn.textContent = "■ Stop"; }
    };
    card.querySelector(".x").onclick = () => { stopSpeak(); card.classList.add("hidden"); };

    if (autoSpeak) { speak(d.verse_text); listenBtn.textContent = "■ Stop"; }
  }

  function showHelp(message) {
    ensurePanel();
    stopSpeak();  // never read crisis content aloud
    card.className = "card help";
    card.innerHTML =
      '<button class="x" title="Dismiss">×</button>' +
      '<div class="ref">A pause, not a verse</div>' +
      '<div class="verse">' + esc(message) + "</div>" +
      '<div class="foot">Resonate · your wellbeing comes first</div>';
    card.querySelector(".x").onclick = () => { stopSpeak(); card.classList.add("hidden"); };
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
