// Resonate content script — one panel beside ANY AI chat.
// Two ways of hearing you, feeding one flow:
//   1. Anchored sites (ChatGPT, Claude): a MutationObserver on the site's stable
//      user-message selector — precise, catches edits and regenerations.
//   2. Every other AI chat (Gemini, Grok, DeepSeek, Copilot, Perplexity, …):
//      composer-capture — we snapshot what you typed the instant you press send,
//      with no site-specific DOM at all, so redesigns can't break it.
// Both send the text + a short rolling history to the background worker -> engine and
// render a quiet, dismissible parchment panel. If detection fails or the engine is
// offline, it does nothing — it never touches or breaks the chat UI.
//
// Panel v2: slides in from the right edge; after a while it folds itself into a small
// wax seal so it never squats on the conversation — click the seal to unfold it again.
// Voice v2: Kokoro voices (Bella / Isabella / George) served by the local engine with a
// reverent "godly" treatment; falls back to the browser's Web Speech if offline.

(function () {
  // Stable per-user id (persisted) so recurring themes accumulate across sessions/days.
  let USER_ID = "chat_" + Math.random().toString(36).slice(2, 10);
  try {
    if (chrome.storage && chrome.storage.sync) {
      chrome.storage.sync.get({ userId: "" }, (r) => {
        if (r.userId) USER_ID = r.userId;
        else chrome.storage.sync.set({ userId: USER_ID });
      });
    }
  } catch (e) {}

  // Which engine answered (local dev vs the hosted Render server) — the background worker
  // decides; we mirror it so the "Ask Ezra" link opens the same server that received the
  // hand-off. Defaults to hosted until the worker replies.
  let ENGINE_BASE = "https://resonate-hg6j.onrender.com";
  try {
    chrome.runtime.sendMessage({ type: "base" }, (r) => {
      if (!chrome.runtime.lastError && r && r.ok && r.base) ENGINE_BASE = r.base;
    });
  } catch (e) {}

  let lastText = "";
  let debounce = null;
  let host = null;
  let shadow = null;
  let card = null;
  let seal = null;
  let foldTimer = null;
  let hovering = false;
  let current = null; // last delivered verse payload

  // --- voice state (persisted) ---
  // Defaults mirror the engine's built-ins; the live list is fetched from /voices at
  // startup (resonate/tts.py is the single source of truth), so a newly tuned Kokoro
  // voice appears here without an extension update. "browser" is always appended.
  let VOICES = ["bella", "isabella", "george", "browser"];
  let VOICE_LABEL = { bella: "Bella", isabella: "Isabella", george: "George", browser: "Browser" };
  // button initials — "Br" keeps Browser distinguishable from Bella's "B"
  let VOICE_INITIAL = { bella: "B", isabella: "I", george: "G", browser: "Br" };
  let voiceId = "bella";
  let autoSpeak = false; // "play by default" — an option, off until chosen
  let audioEl = null;
  let speaking = false;

  function rebuildVoices(list) {
    const ids = [], labels = {}, initials = {}, used = new Set();
    for (const v of list.concat([{ id: "browser", label: "Browser" }])) {
      if (!v || !v.id || ids.includes(v.id)) continue;
      const label = String(v.label || v.id).split("—")[0].trim() || v.id;
      let ini = label[0].toUpperCase();
      if (used.has(ini)) ini = label.slice(0, 2); // Bella takes "B", Browser becomes "Br"
      used.add(ini);
      ids.push(v.id); labels[v.id] = label; initials[v.id] = ini;
    }
    if (ids.length < 2) return; // keep the defaults over a degenerate list
    VOICES = ids; VOICE_LABEL = labels; VOICE_INITIAL = initials;
    if (!VOICES.includes(voiceId)) voiceId = VOICES[0];
  }
  // Hosted fallback: the server can't run the Kokoro model, so each named voice is mapped to
  // a DISTINCT browser voice + tuning that approximates its Kokoro character. This keeps our
  // three voices (Bella / Isabella / George) in the panel — instead of exposing raw OS voice
  // names — and makes them sound different from one another even on a one-voice machine
  // (before this, all three fell back to a single browser default: three names, one sound).
  let kokoroAvailable = false;   // true only when the engine reports real Kokoro voices
  const FALLBACK = {
    bella:    { prefer: ["Samantha", "Microsoft Aria", "Google US English", "Microsoft Michelle", "Microsoft Zira"], rate: 0.90, pitch: 0.98 },
    isabella: { prefer: ["Google UK English Female", "Microsoft Sonia", "Microsoft Libby", "Serena", "Kate"], rate: 0.88, pitch: 1.06 },
    george:   { prefer: ["Google UK English Male", "Microsoft Ryan", "Daniel", "Microsoft George", "Arthur", "Microsoft David"], rate: 0.92, pitch: 0.80 },
  };
  function pickVoiceFrom(prefer) {
    let vs = [];
    try { vs = window.speechSynthesis.getVoices() || []; } catch (e) {}
    const en = vs.filter((v) => /^en/i.test(v.lang || ""));
    for (const name of (prefer || [])) { const m = en.find((v) => v.name && v.name.includes(name)); if (m) return m; }
    return null; // no preferred match — caller uses a generic en voice with the profile's tuning
  }

  try {
    chrome.runtime.sendMessage({ type: "voices" }, (resp) => {
      const d = !chrome.runtime.lastError && resp && resp.ok && resp.data;
      if (d && d.ok && d.available && Array.isArray(d.voices) && d.voices.length) {
        kokoroAvailable = true;
        rebuildVoices(d.voices);       // engine has real Kokoro voices (local dev)
      } else {
        // hosted: no Kokoro — keep Bella / Isabella / George, each backed by a tuned
        // browser voice at speak() time (see FALLBACK). Warm the browser voice list.
        kokoroAvailable = false;
        try { window.speechSynthesis.getVoices(); window.speechSynthesis.onvoiceschanged = () => {}; } catch (e) {}
      }
    });
  } catch (e) {}
  try {
    if (chrome.storage && chrome.storage.sync)
      chrome.storage.sync.get({ autoSpeak: false, voiceId: "bella" }, (r) => {
        autoSpeak = !!r.autoSpeak;
        if (VOICES.includes(r.voiceId)) voiceId = r.voiceId;
      });
  } catch (e) {}
  try { window.speechSynthesis.getVoices(); window.speechSynthesis.onvoiceschanged = () => {}; } catch (e) {}

  function persistVoice() {
    try {
      if (chrome.storage && chrome.storage.sync) chrome.storage.sync.set({ autoSpeak, voiceId });
    } catch (e) {}
  }

  // ---------- speech ----------
  function pickBrowserVoice() {
    let vs = [];
    try { vs = window.speechSynthesis.getVoices() || []; } catch (e) {}
    const prefer = ["Google UK English Female", "Microsoft Aria", "Microsoft Sonia", "Microsoft Jenny",
                    "Samantha", "Microsoft Zira", "Google US English", "Daniel"];
    for (const name of prefer) { const m = vs.find((v) => v.name && v.name.includes(name)); if (m) return m; }
    return vs.find((v) => /^en/i.test(v.lang || "")) || vs[0] || null;
  }

  function speakBrowser(text, name, profile) {
    try {
      const synth = window.speechSynthesis; if (!synth) return endSpeak();
      synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      let v = null;
      if (name) {
        try { v = (synth.getVoices() || []).find((x) => x.name === name) || null; } catch (e) {}
      }
      if (!v && profile) v = pickVoiceFrom(profile.prefer); // map a named voice to its browser match
      if (!v) v = pickBrowserVoice();
      if (v) u.voice = v;
      // per-voice tuning approximates the Kokoro preset (deeper for George, brighter for Isabella);
      // the pitch/rate differences also keep the three distinct when only one OS voice exists.
      u.rate = profile ? profile.rate : 0.92;
      u.pitch = profile ? profile.pitch : 0.96;
      u.volume = 1;
      u.onend = endSpeak; u.onerror = endSpeak;
      speaking = true; reflectSpeaking();
      synth.speak(u);
    } catch (e) { endSpeak(); }
  }

  function speak(text) {
    stopSpeak(false);
    if (voiceId === "browser" || voiceId.indexOf("bv:") === 0) {
      speakBrowser(text, voiceId.indexOf("bv:") === 0 ? voiceId.slice(3) : null);
      return;
    }
    const profile = FALLBACK[voiceId] || null;
    // Hosted (no Kokoro): go straight to the mapped browser voice — skip the /tts round trip
    // that would fail and collapse all three names onto one identical browser default.
    if (!kokoroAvailable) { speakBrowser(text, null, profile); return; }
    try {
      chrome.runtime.sendMessage({ type: "tts", voice: voiceId, text }, (resp) => {
        if (chrome.runtime.lastError || !resp || !resp.ok) { speakBrowser(text, null, profile); return; }
        try {
          const bin = atob(resp.b64);
          const bytes = new Uint8Array(bin.length);
          for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
          const url = URL.createObjectURL(new Blob([bytes], { type: resp.mime || "audio/wav" }));
          audioEl = new Audio(url);
          audioEl.onended = () => { URL.revokeObjectURL(url); endSpeak(); };
          audioEl.onerror = () => { URL.revokeObjectURL(url); endSpeak(); };
          speaking = true; reflectSpeaking();
          audioEl.play().catch(() => { speaking = false; speakBrowser(text, null, profile); });
        } catch (e) { speakBrowser(text, null, profile); }
      });
    } catch (e) { speakBrowser(text, null, profile); }
  }

  function stopSpeak(reflect = true) {
    try { window.speechSynthesis.cancel(); } catch (e) {}
    if (audioEl) { try { audioEl.pause(); } catch (e) {} audioEl = null; }
    speaking = false;
    if (reflect) reflectSpeaking();
  }

  function endSpeak() { speaking = false; reflectSpeaking(); scheduleFold(); }

  function reflectSpeaking() {
    if (card) {
      const b = card.querySelector(".listen");
      if (b) {
        b.textContent = speaking ? "◼" : "♪";
        b.title = speaking ? "Stop reading" : "Listen — read this verse aloud";
        b.classList.toggle("on", speaking);
      }
    }
    if (seal) seal.classList.toggle("speaking", speaking);
  }

  // ---------- panel skin ----------
  // Parchment / aged-manuscript (paper #efe9df, ink #211d17, clay #a65b43), kept in sync
  // with web/panel-preview.html. The card enters from the right edge like a slipped note,
  // and folds into a small wax seal when it has been quiet for a while.
  const PANEL_CSS = `
    :host-context(html){}
    .wrap{display:flex;flex-direction:column;align-items:flex-end;gap:0}
    .card{width:340px;box-sizing:border-box;
      font-family:'Space Grotesk',ui-sans-serif,-apple-system,'Segoe UI',Roboto,sans-serif;color:#211d17;
      background:radial-gradient(130% 120% at 100% 0%, rgba(166,91,67,.07), transparent 58%),
        linear-gradient(177deg,#efe9df 0%,#e9e1d3 58%,#e3d7c4 100%);
      border:1px solid rgba(33,29,23,.22);border-radius:16px;padding:19px 20px 13px;
      box-shadow:0 18px 50px rgba(33,29,23,.28), inset 0 1px 0 rgba(255,255,255,.5);
      position:relative;
      transform-origin:100% 100%;
      animation:slidein .5s cubic-bezier(.21,.68,.33,1) both;
      transition:transform .38s cubic-bezier(.55,.06,.68,.19), opacity .38s ease}
    .card.hidden{display:none}
    .card.out{transform:translateX(380px);opacity:0}
    .card.fold{transform:scale(.12) translate(46px,54px);opacity:0}
    @keyframes slidein{from{opacity:0;transform:translateX(380px)}to{opacity:1;transform:none}}
    .card::before{content:"";position:absolute;inset:7px;border:1px solid rgba(33,29,23,.13);
      border-radius:11px;pointer-events:none}
    .x{position:absolute;top:9px;right:12px;background:none;border:none;color:#9a8f7f;font-size:16px;
      cursor:pointer;line-height:1;font-family:inherit;z-index:1}
    .x:hover{color:#a65b43}
    .ref{font-size:10.5px;letter-spacing:.3em;text-transform:uppercase;color:#a65b43;margin:0 0 10px;padding-right:18px}
    .ref .tr{color:#a89c8a;letter-spacing:.2em}
    .ref::after{content:"";display:block;width:32px;height:1px;background:#a65b43;opacity:.55;margin-top:8px}
    .verse{font-family:'Cormorant Garamond','EB Garamond','Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif;
      font-size:20px;line-height:1.42;color:#211d17;font-weight:500}
    .bridge{margin-top:11px;font-family:'Cormorant Garamond','EB Garamond',Georgia,serif;font-size:14px;
      font-style:italic;color:#6b6358;border-top:1px solid rgba(33,29,23,.13);padding-top:10px}
    .mem{margin-top:10px;font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;color:#a65b43;opacity:.92}
    /* --- compact icon row: listen / voice / auto / reel — titles say the rest --- */
    .icons{display:flex;align-items:center;gap:8px;margin-top:12px}
    .ico{width:27px;height:27px;border-radius:50%;box-sizing:border-box;flex:0 0 auto;
      border:1px solid rgba(166,91,67,.45);color:#a65b43;background:none;cursor:pointer;
      display:flex;align-items:center;justify-content:center;font-family:inherit;font-size:12px;
      line-height:1;padding:0;text-decoration:none;
      transition:background .18s ease, transform .18s ease}
    .ico:hover{background:rgba(166,91,67,.12);transform:translateY(-1px)}
    .ico.on{background:linear-gradient(160deg,#a65b43,#8a4a35);color:#f3e4d5;border-color:transparent;
      box-shadow:inset 0 1px 0 rgba(255,255,255,.25)}
    .ico.voice{font-size:11.5px;font-weight:600;font-family:'Cormorant Garamond',Georgia,serif}
    .story{display:block;width:100%;box-sizing:border-box;margin-top:12px;text-align:center;cursor:pointer;
      font-family:inherit;font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:#efe9df;
      background:linear-gradient(160deg,#a65b43,#8a4a35);border:none;border-radius:999px;padding:7px 12px;
      box-shadow:inset 0 1px 0 rgba(255,255,255,.25), 0 2px 8px rgba(138,74,53,.35)}
    .story:hover{filter:brightness(1.06)}
    .story[disabled]{opacity:.6;cursor:wait}
    .storytext{font-family:'Cormorant Garamond','EB Garamond',Georgia,serif;font-size:15.5px;line-height:1.55;
      color:#211d17;max-height:280px;overflow-y:auto;padding-right:6px;white-space:pre-line}
    .storytext::-webkit-scrollbar{width:5px}
    .storytext::-webkit-scrollbar-thumb{background:rgba(166,91,67,.35);border-radius:3px}
    .backlink{font-family:inherit;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:#a89c8a;
      background:none;border:none;cursor:pointer;padding:0}
    .backlink:hover{color:#a65b43}
    .label{margin-top:9px;font-size:8.5px;letter-spacing:.08em;color:#a89c8a;line-height:1.5}
    .foot{margin-top:11px;font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:#a89c8a}
    .card.help .verse{font-size:16.5px}
    .card.help .ref::after{width:46px}
    /* --- the wax seal (folded state): quiet, small, glad to wait --- */
    .seal{width:46px;height:46px;border-radius:50%;cursor:pointer;border:none;padding:0;
      background:radial-gradient(circle at 34% 30%, #c07a5e 0%, #a65b43 42%, #7d3f2c 100%);
      box-shadow:0 6px 18px rgba(33,29,23,.35), inset 0 2px 4px rgba(255,255,255,.28), inset 0 -3px 6px rgba(60,25,14,.5);
      color:#f3e4d5;font-family:'Cormorant Garamond',Georgia,serif;font-size:24px;font-weight:600;line-height:1;
      display:flex;align-items:center;justify-content:center;position:relative;
      animation:pop .32s cubic-bezier(.22,.61,.36,1) both}
    .seal::after{content:"";position:absolute;inset:5px;border-radius:50%;border:1px solid rgba(243,228,213,.4)}
    .seal:hover{transform:scale(1.08)}
    .seal.hidden{display:none}
    .seal.speaking{animation:pulse 1.6s ease-in-out infinite}
    @keyframes pop{from{opacity:0;transform:scale(.5)}to{opacity:1;transform:none}}
    @keyframes pulse{0%,100%{box-shadow:0 6px 18px rgba(33,29,23,.35), 0 0 0 0 rgba(166,91,67,.45)}
      50%{box-shadow:0 6px 18px rgba(33,29,23,.35), 0 0 0 9px rgba(166,91,67,0)}}
    @media (prefers-reduced-motion: reduce){
      .card,.seal{animation:none !important;transition:none !important}
      .seal.speaking{animation:none !important}
    }`;

  const FOLD_AFTER_MS = 14000;   // idle time before the card folds into the seal
  const FOLD_ANIM_MS = 420;

  function ensurePanel() {
    if (host) return;
    host = document.createElement("div");
    // Bottom-right, floating above the composer; never overlaps the input on a
    // normal-width window because the chat column is centered.
    host.style.cssText = "position:fixed;right:18px;bottom:104px;z-index:2147483647;";
    shadow = host.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = PANEL_CSS;
    const wrap = document.createElement("div");
    wrap.className = "wrap";
    card = document.createElement("div");
    card.className = "card hidden";
    // a quiet companion announces itself quietly: polite live region, named dialog
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-label", "Resonate — a verse for this moment");
    card.setAttribute("aria-live", "polite");
    seal = document.createElement("button");
    seal.className = "seal hidden";
    seal.title = "Resonate — open the verse";
    seal.setAttribute("aria-label", "Resonate — open the verse");
    seal.textContent = "R";
    seal.onclick = unfold;
    wrap.append(card, seal);
    shadow.append(style, wrap);
    document.documentElement.appendChild(host);

    card.addEventListener("mouseenter", () => { hovering = true; clearTimeout(foldTimer); });
    card.addEventListener("mouseleave", () => { hovering = false; scheduleFold(); });
  }

  function scheduleFold() {
    clearTimeout(foldTimer);
    if (!card || card.classList.contains("hidden")) return;
    foldTimer = setTimeout(() => {
      if (hovering || speaking) { scheduleFold(); return; } // busy — check again later
      fold();
    }, FOLD_AFTER_MS);
  }

  function fold() {
    if (!card || card.classList.contains("hidden")) return;
    card.classList.add("fold");
    setTimeout(() => {
      card.classList.add("hidden");
      card.classList.remove("fold");
      seal.classList.remove("hidden");
      reflectSpeaking();
    }, FOLD_ANIM_MS);
  }

  function unfold() {
    seal.classList.add("hidden");
    card.classList.remove("hidden", "out", "fold");
    // retrigger the slide-in
    card.style.animation = "none";
    void card.offsetWidth; // reflow
    card.style.animation = "";
    scheduleFold();
  }

  function dismiss() {
    stopSpeak();
    clearTimeout(foldTimer);
    if (!card) return;
    card.classList.add("out");
    setTimeout(() => { card.classList.add("hidden"); card.classList.remove("out"); }, 400);
    if (seal) seal.classList.add("hidden");
  }

  function esc(s) {
    return (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function freshCard(cls) {
    ensurePanel();
    seal.classList.add("hidden");
    card.classList.remove("hidden", "out", "fold");
    card.className = "card " + cls;
    card.style.animation = "none";
    void card.offsetWidth; // restart the slide-in for every new arrival
    card.style.animation = "";
  }

  function showVerse(d) {
    stopSpeak(false);
    current = d;
    freshCard("verse");
    const reel = d.reel || null;
    const reelTitle = reel && reel.kind === "story" ? "Watch this verse's story reel"
                                                    : "Read this verse on YouVersion";
    card.innerHTML =
      '<button class="x" title="Dismiss" aria-label="Dismiss">×</button>' +
      '<div class="ref">' + esc(d.reference) + ' <span class="tr">' + esc(d.translation) + "</span></div>" +
      '<div class="verse">' + esc(d.verse_text) + "</div>" +
      '<div class="bridge">' + esc(d.bridge) + "</div>" +
      (d.memory_note ? '<div class="mem">' + esc(d.memory_note) + "</div>" : "") +
      '<div class="icons">' +
        '<button class="ico listen" title="Listen — read this verse aloud" aria-label="Listen — read this verse aloud">♪</button>' +
        '<button class="ico voice" title="Voice: ' + esc(VOICE_LABEL[voiceId]) + ' — click to change" ' +
          'aria-label="Change voice (now ' + esc(VOICE_LABEL[voiceId]) + ')">' +
          esc(VOICE_INITIAL[voiceId]) + "</button>" +
        '<button class="ico auto' + (autoSpeak ? " on" : "") + '" title="Auto-play every verse aloud (' +
          (autoSpeak ? "on" : "off") + ') — click to toggle" aria-label="Auto-play every verse aloud, now ' +
          (autoSpeak ? "on" : "off") + '">⟳</button>' +
        (reel ? '<a class="ico reelico" href="' + esc(reel.url) +
                '" target="_blank" rel="noopener noreferrer" title="' + reelTitle +
                '" aria-label="' + reelTitle + '">▷</a>' : "") +
        '<a class="ico ezra" href="' + esc(ENGINE_BASE + "/guide.html?uid=" + encodeURIComponent(USER_ID)) +
            '" target="_blank" rel="noopener noreferrer" ' +
            'title="Ask Ezra — carry this moment into a deeper conversation (you choose to share it)" ' +
            'aria-label="Ask Ezra about this moment">☎</a>' +
      "</div>" +
      '<button class="story" aria-label="Your story — a reflection woven for you">✦ Your story</button>' +
      '<div class="foot">Resonate · nothing you write is stored</div>';

    card.querySelector(".listen").onclick = () => {
      if (speaking) stopSpeak();
      else speak(d.verse_text);
    };
    const ezra = card.querySelector(".ezra");
    if (ezra) ezra.onclick = () => {
      // hand the moment over engine-side (single-read, short-lived) so the person's
      // words never travel in the URL — history and logs stay clean
      try { chrome.runtime.sendMessage({ type: "handoff", userId: USER_ID, text: lastText.slice(0, 600) }); } catch (e) {}
    };
    card.querySelector(".story").onclick = (e) => {
      const btn = e.currentTarget;
      btn.disabled = true; btn.textContent = "✦ weaving your story…";
      try {
        chrome.runtime.sendMessage({
          type: "story", userId: USER_ID, text: lastText,
          beat: d.beat || {}, memoryNote: d.memory_note || null,
          verse: { reference: d.reference, usfm: d.usfm, verse_text: d.verse_text,
                   translation: d.translation },
        }, (resp) => {
          if (chrome.runtime.lastError || !resp || !resp.ok || !resp.data || !resp.data.ok) {
            btn.disabled = false; btn.textContent = "✦ Your story";
            return;
          }
          showStory(d, resp.data.story);
        });
      } catch (err) { btn.disabled = false; btn.textContent = "✦ Your story"; }
    };
    card.querySelector(".voice").onclick = (e) => {
      voiceId = VOICES[(VOICES.indexOf(voiceId) + 1) % VOICES.length];
      e.currentTarget.textContent = VOICE_INITIAL[voiceId];
      e.currentTarget.title = "Voice: " + VOICE_LABEL[voiceId] + " — click to change";
      persistVoice();
      if (speaking) { stopSpeak(false); speak(d.verse_text); } // hear the new voice at once
    };
    card.querySelector(".auto").onclick = (e) => {
      autoSpeak = !autoSpeak;
      e.currentTarget.classList.toggle("on", autoSpeak);
      e.currentTarget.title = "Auto-play every verse aloud (" + (autoSpeak ? "on" : "off") + ") — click to toggle";
      persistVoice();
      if (autoSpeak && !speaking) speak(d.verse_text);
    };
    card.querySelector(".x").onclick = dismiss;

    if (autoSpeak) speak(d.verse_text);
    scheduleFold();
  }

  function showStory(d, story) {
    stopSpeak(false);
    clearTimeout(foldTimer); // long-form reading — never fold mid-story
    freshCard("verse");
    card.innerHTML =
      '<button class="x" title="Dismiss" aria-label="Dismiss">×</button>' +
      '<div class="ref">Your story · ' + esc(story.title) + ' <span class="tr">' + esc(story.reference) + "</span></div>" +
      '<div class="storytext">' + esc(story.text) + "</div>" +
      '<div class="label">' + esc(story.label) + "</div>" +
      '<div class="icons">' +
        '<button class="ico listen" title="Listen — read this story aloud" aria-label="Listen — read this story aloud">♪</button>' +
        '<button class="backlink">← back to the verse</button>' +
      "</div>" +
      '<div class="foot">Resonate · woven for you · your words aren\'t stored</div>';
    card.querySelector(".listen").onclick = () => {
      if (speaking) stopSpeak();
      else speak(story.text);
    };
    card.querySelector(".backlink").onclick = () => { stopSpeak(); showVerse(d); };
    card.querySelector(".x").onclick = dismiss;
  }

  function showHelp(hold) {
    stopSpeak(); // never read crisis content aloud
    current = null;
    freshCard("help");
    const g = (hold && hold.guardian) || {};
    card.innerHTML =
      '<button class="x" title="Dismiss" aria-label="Dismiss">×</button>' +
      '<div class="ref">A pause, not a verse</div>' +
      '<div class="verse">' + esc(hold && hold.message ? hold.message : "") + "</div>" +
      (g.dispatched ? '<div class="mem" title="You registered your guardians and consented to this — what you wrote stays private.">' +
        "Your guardians have been quietly notified.</div>" : "") +
      '<div class="foot">Resonate · your wellbeing comes first</div>';
    card.querySelector(".x").onclick = dismiss;
    clearTimeout(foldTimer); // a help card never folds itself away
  }

  // Sites with a stable user-message DOM anchor. Everything else relies purely on
  // composer-capture below (which also runs here, as a belt-and-braces instant path).
  const HOST = location.hostname.replace(/^www\./, "");
  const MESSAGE_SELECTORS = {
    "chatgpt.com": '[data-message-author-role="user"]',
    "chat.openai.com": '[data-message-author-role="user"]',
    "claude.ai": '[data-testid="user-message"]',
  };
  const SEL = MESSAGE_SELECTORS[HOST];

  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();

  function userMessages() {
    const nodes = document.querySelectorAll(SEL);
    return Array.from(nodes).map((n) => norm(n.innerText)).filter(Boolean);
  }

  function handle(all) {
    const text = all.length ? norm(all[all.length - 1]) : "";
    if (!text || text === lastText) return;
    lastText = text;
    const history = all.slice(-4, -1); // up to 3 prior messages — conversation context
    try {
      chrome.runtime.sendMessage({ type: "resonate", text, history, userId: USER_ID }, (resp) => {
        if (chrome.runtime.lastError || !resp || !resp.ok) return; // engine offline -> stay invisible
        const data = resp.data || {};
        const policy = data.policy || {};
        const deliveries = data.deliveries || [];
        if (policy.safety) {
          const hold = deliveries.find((d) => d.status === "safety_hold");
          if (hold) showHelp(hold);
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

  // -- anchored path: observe the site's own user-message nodes --
  const observer = SEL
    ? new MutationObserver(() => {
        clearTimeout(debounce);
        debounce = setTimeout(() => handle(userMessages()), 600);
      })
    : null;

  // -- universal path: capture the composer at the moment of send --
  // Works on any chat UI: the message box is a <textarea> or contenteditable, and
  // sending is Enter (without Shift) or a send-ish button. We read the words in the
  // capture phase, before the site clears the box. History is our own rolling log.
  const sentLog = [];
  let lastComposer = null;

  // The editable the user types into: a <textarea>, or the ROOT of a contenteditable.
  // Rich editors (ChatGPT, Claude, Gemini) fire the keydown on a nested node, so we
  // climb out of any inline child — otherwise we'd capture one span, not the message.
  function composerRoot(el) {
    if (!el || (host && host.contains(el))) return null; // never our own panel
    if (el.tagName === "TEXTAREA") return el;
    if (!el.isContentEditable) return null;
    let root = el;
    while (root.parentElement && root.parentElement.isContentEditable) root = root.parentElement;
    return root;
  }

  function composerText(el) {
    return norm(el.tagName === "TEXTAREA" ? el.value : (el.innerText || el.textContent || ""));
  }

  function captureSend(el) {
    // resolve to the editable root; fall back to the last one we saw focused
    const root = composerRoot(el) ||
                 (lastComposer && document.contains(lastComposer) ? lastComposer : null);
    if (!root) return;
    const text = composerText(root);
    if (text.length < 5) return;                       // ignore stray Enters / 1-word noise
    if (sentLog[sentLog.length - 1] === text) return;  // dedupe the same send
    sentLog.push(text);
    if (sentLog.length > 6) sentLog.shift();
    handle(sentLog.slice());
  }

  function startComposerCapture() {
    document.addEventListener("focusin", (e) => {
      const root = composerRoot(e.target);
      if (root) lastComposer = root;
    }, true);
    // Enter (plain, or with the ctrl/cmd send-shortcut some sites use) — capture in the
    // capture phase, before the site clears the box. Shift+Enter / IME are newlines.
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" || e.shiftKey || e.isComposing) return;
      captureSend(e.target);
    }, true);
    // click on a send/submit control — read the last-focused composer before it clears
    document.addEventListener("click", (e) => {
      const btn = e.target && e.target.closest && e.target.closest('button, [role="button"], [type="submit"]');
      if (!btn || (host && host.contains(btn))) return;
      const label = ((btn.getAttribute("aria-label") || "") + " " +
                     (btn.getAttribute("data-testid") || "") + " " +
                     (btn.getAttribute("title") || "") + " " + (btn.type || "")).toLowerCase();
      if (/send|submit/.test(label)) captureSend(lastComposer);
    }, true);
  }

  function start() {
    if (observer) observer.observe(document.body, { childList: true, subtree: true });
    startComposerCapture(); // on anchored sites too — instant, and handle() dedupes
  }
  if (document.body) start();
  else window.addEventListener("DOMContentLoaded", start);
})();
