# Resonate — 3-Minute Demo Video Script (v2 — two-scenario cut)

**Title:** *Resonate — Scripture, where you already are*
**Runtime target:** 2:55 (hard ceiling 3:00) · **VO budget:** ~400 words (≈140 wpm, unhurried)
**Tone:** calm, intimate, reverent — never preachy. Let silence breathe.
**Music:** soft ambient piano/strings, low; swell once at the reel beat (≈2:05).
**Structure (user's cut):** two real-life scenarios — an emotional conversation, then study
pressure — each ends with the person *hearing* the verse and one of them tapping **Watch this
verse's story** into a reel that lifts them. Realistic people, inner-voice narration ("mind
sounds"), HD.

> Honesty rule (judges review code): everything shown is really built. The panel, the fold-away
> wax seal, the three voices, the reel button, memory, restraint and the crisis card all work
> today (offline mock). Film against live keys after 2026-07-06 so verse text is real YouVersion.
> The story-reels themselves are produced FOR the film (AI video, e.g. Higgsfield/Runway/Veo) and
> presented as the format "hosted on YouVersion or a related platform" — say it exactly that way.

---

## COLD OPEN — the honest problem (0:00–0:25)
| Time | Visual | Audio | On-screen text |
|---|---|---|---|
| 0:00 | Dark room, late night. A tired face lit by a screen. ChatGPT cursor blinking. | *(2s silence)* VO: "Every day, millions of people type the most honest words of their lives — not to a friend. To an AI." | |
| 0:12 | Slow push on the empty input. | VO: "And in that moment, Scripture has never been there. Not because it doesn't belong — because no one built the bridge." | **Until now.** |

## SCENARIO 1 — the heavy evening (0:25–1:25)
*Realistic person A (choose a relatable adult; face allowed, warm grade). Their inner voice is
the narration — mic'd close, like thought.*

| Time | Visual | Audio | Notes |
|---|---|---|---|
| 0:25 | A types to ChatGPT: **"I feel like I'm failing everyone lately. I can't keep up."** | Inner voice: "You don't say this out loud. You type it." | real extension, live |
| 0:37 | ChatGPT replies normally… then, bottom-right, the **parchment card slides in from the side** — GALATIANS 6:9 + bridge line. | *(soft paper sound)* Inner voice: "…what is that?" | the slide-in is the beat — hold it |
| 0:48 | Close-up of the card. Cursor taps **▸ Listen**. | **George's voice** (deep, unhurried, chapel-quiet): *"And let us not be weary in well doing: for in due season we shall reap, if we faint not."* | Kokoro `bm_george` godly preset — record from /tts |
| 1:02 | A sits back. The card quietly **folds itself into a small wax seal** in the corner. | Inner voice: "It didn't shout. It didn't stay. It just… waited." | the fold is the restraint beat |
| 1:10 | A taps the seal → card unfolds → taps **▷ Watch this verse's story**. | *(music lifts gently)* | |
| 1:14 | **REEL 1 (vertical, HD):** ~10s excerpt — a farmer in bad weather keeps sowing; season turns; harvest. Cut to A's face, lit. | Reel VO (Isabella): "…in due season, we shall reap." Inner voice: "Okay. One more day." | produce with AI video; caption: *Story reels — a format for YouVersion & partners* |

## SCENARIO 2 — the exam week (1:25–2:20)
*Realistic person B (student). Faster cutting — study pressure energy.*

| Time | Visual | Audio | Notes |
|---|---|---|---|
| 1:25 | Montage: books, tabs, energy drink. B types: **"I'm studying with you all night, I'm so anxious about tomorrow, I can't stop worrying."** | Inner voice: "Third all-nighter. My chest is tight." | |
| 1:37 | The card slides in: MATTHEW 6:34. **auto-read is ON** — it speaks as it arrives. | **Bella's voice**: *"Take therefore no thought for the morrow…"* | "play by default" beat |
| 1:48 | B keeps studying; the card folds to the seal on its own; B glances, half-smiles, keeps working. | Inner voice: "It waits better than I do." | restraint again — never blocks study |
| 1:55 | Quick honesty beats, rapid cuts: **"what's the capital of France?" → silence.** A crisis-adjacent phrase → the **help card** (blur/soft). | VO: "Ask something ordinary — silence. And if it ever hears real darkness, it never answers with a verse. It points to help." | the safety beat — protect it in any cut |
| 2:05 | *(music swell)* B returns after days; panel shows **"You've returned to anxiety — 4× lately."** B taps the reel. **REEL 2:** ~8s — birds over a field at dawn. | Reel VO: "…your heavenly Father feedeth them." Inner voice: "It remembers my story." | series memory — real feature |

## CLOSE — the bridge (2:20–2:55)
| Time | Visual | Audio | On-screen text |
|---|---|---|---|
| 2:20 | Fast cuts: same engine in **VS Code** margins; the panel on a phone-width chatgpt.com window; the three voice names cycling on the card. | VO: "One engine. Your chat, your editor, your voice — Bella, Isabella, or George. You choose where Scripture meets you." | |
| 2:36 | Pull back from the glowing screen; the wax seal glows softly in the corner. | VO: "Two billion people live in these spaces. Resonate is the bridge — present, reverent, never intruding." | |
| 2:46 | End card: **RESONATE** wordmark on parchment. | *(quiet)* "Scripture, where you already are." | Powered by YouVersion Platform + Gloo AI Studio · github.com/krizz711/resonate |

---

## Capture checklist
- [ ] Live extension on chatgpt.com (after keys: `RESONATE_MODE=live`) — slide-in, fold-to-seal,
      unfold, dismiss. (If a controlled no-flake backdrop is ever needed, restore
      `web/mock-chat.html` from git history — removed from the public UI 2026-07-13.)
- [ ] Voice takes from the engine itself: `http://127.0.0.1:8765/tts?voice=george&text=...`
      (repeat for bella/isabella) — save WAVs for the edit. Pick winners in `data/voice-lab/index.html`.
- [ ] Restraint beat (neutral msg → silence), safety beat (help card — mild phrasing, blur).
- [ ] Series-memory line ("returned N× lately") — real, appears after recurring themes.
- [ ] **Reels ×2 (the big lift):** vertical 1080×1920, ~10s each, realistic people, no on-screen
      text errors. AI video (Higgsfield / Runway / Veo — pick by trial). Drop files/links into
      `data/reels.json` so the button opens YOUR reel in the film.
- [ ] B-roll: hands, night room, books, dawn. Faces warm and relatable.
- [ ] End card in the parchment palette (paper #efe9df, ink #211d17, clay #a65b43).

## Editing notes
- The **fold-to-seal** and the **reel tap** are the two moments judges will remember — hold each
  a extra half-second. The safety beat is what separates this from "a verse generator."
- Inner-voice narration: record dry and close; duck music under it.
- **Do NOT fake anything.** Everything above exists; if a shot isn't ready, cut it rather than mock it.
