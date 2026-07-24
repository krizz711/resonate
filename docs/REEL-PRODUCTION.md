# Resonate — AI-Video Production Pack (reels + scenario B-roll)

Companion to [`VIDEO-SCRIPT.md`](./VIDEO-SCRIPT.md). This file holds the **generation-ready prompts
and settings** for every AI-video shot in the 3-minute demo film. Engine-agnostic: paste into
Higgsfield (Seedance/Veo/Kling), Google Veo (AI Studio), Kling, or Runway. Keep the film itself
honest — screen-capture of the real extension is real footage, never AI.

**Deliverables (your "3 videos, 1 main"):**
1. **MAIN** — the 2:55 demo film (assembled, not generated). See `VIDEO-SCRIPT.md`.
2. **REEL 1** — Galatians 6:9, farmer/harvest, 9:16, ~10s.
3. **REEL 2** — Matthew 6:26/34, birds at dawn, 9:16, ~8–10s.

Global settings for every clip below: **9:16 (1080×1920) for reels, 16:9 (1920×1080) for B-roll ·
24fps · film grain · shallow depth of field · NO on-screen text / captions / logos / watermark.**
Global negative prompt: `text, captions, subtitles, watermark, logo, distorted hands, extra fingers,
warped faces, morphing, flicker, modern machinery, cars, phones`.

Reverent tone rule: unhurried camera, natural light, muted earthy palette, let motion breathe.

---

## Veo 3.1 Fast (Google AI Studio) — settings + paste-ready prompts
Engine of record: **Veo 3.1 Fast** (`veo-3.1-fast-generate-preview`) in Google AI Studio, PRO tier.
Run settings for BOTH reels: **Aspect ratio 9:16** (change it from the 16:9 default!) · Duration **8s**
· **24 fps** · 720p · Number of results **1** (conserve daily Veo quota). Veo adds native ambient
audio — ignore it; we strip and replace with Kokoro VO + soft piano in the edit. One 8s clip = one
whole reel (no need to split into 1A/1B). Reserve Veo quota for the two reels; pull scenario B-roll
from a free tier.

**Reel 1 — paste:**
> Vertical 9:16 cinematic film, photorealistic, 24fps, shallow depth of field, subtle film grain. A
> weathered older farmer in simple linen work clothes walks slowly across a muddy furrowed field,
> sowing seed by hand, under a grey wind-driven overcast sky with light drifting rain. The camera
> tracks smoothly alongside him at a calm, unhurried pace. Halfway through, a seamless time-lapse
> dissolve turns the same field into tall golden ripe wheat glowing in warm low evening sun; the
> farmer now stands among the harvest, gently running his hand across the grain with quiet peace on
> his face. Earthy palette shifting from cold grey to warm gold, soft natural light, reverent mood.
> Ambient wind and rustling grain only, no voices, no music. No text, no captions, no subtitles, no
> watermark, no logos.

**Reel 2 — paste:**
> Vertical 9:16 cinematic film, photorealistic, 24fps, shallow depth of field, subtle film grain. A
> small flock of little birds lifts off and wheels gracefully over a dew-soft green meadow at first
> light, low morning mist drifting across the grass, the sun breaking warm and golden on the horizon.
> The camera tilts slowly upward, following the birds into the brightening sky with gentle,
> weightless motion. Warm dawn palette, soft golden haze, restrained natural lens flare, deeply
> peaceful and reverent mood. Ambient soft breeze and distant birdsong only, no voices, no music. No
> text, no captions, no subtitles, no watermark, no logos.

Save outputs as `reel1_harvest.mp4` and `reel2_dawn.mp4` in `resonate/demo-video/`.

---

## MAIN FILM (16:9) — Veo B-roll shot prompts (v2, single-clip arcs)
Cinematic emotional B-roll for the 2:40 cut. **16:9 · 8s each.** Rule: never let Veo render the app UI
or verse text — generate clean emotion + a warm out-of-focus screen glow, then composite the REAL
Resonate card + real YouVersion verse in the edit (fixes honesty, copyright, brand, and Veo's
text-mangling). App is **Resonate** ("Scripture, where you already are"), not "Ezra". Each scenario is
one continuous clip (anxious → relieved) so faces never need to match across cuts — no character sheets.

- **V1 Cold open** — drone pull-back from a rainy night apartment, lightning, blue-grey, moody.
- **V2 Anxiety→relief** — young woman hunched at a night desk, blue laptop glow, rain; warm glow rises
  from phone, tension melts to a faint smile. Screen unreadable.
- **V3 Studying** — male student, round glasses, cold-lit room of books/papers, hands in hair; warm
  sunlight blooms, sits upright, resumes writing with quiet confidence.
- **V4 Coding** — bearded dev, charcoal hoodie, glasses, monitors glowing red; amber glow in glasses,
  jaw relaxes, monitor shifts red→green, relieved smile.
- **V5 Loneliness→peace** — woman alone at evening dinner scrolling; warm glow from phone, sets it
  down, turns to window, peaceful smile.
- **V6 Finale sunrise** — golden-hour drone push over city skyline, birds, HDR, hopeful.
- **V7 Finale human** — person on a sunlit park bench with phone, dappled bokeh trees, calm hope.

**LOCKED realism style block** (append to every V-prompt — replaces the old glossy tail, which pushed
a plasticky AI-ad look). Keep light shifts subtle ("slowly, subtly warms", never "floods the room"):
`Shot on ARRI Alexa, vintage 35mm prime lens, natural available light, candid documentary realism,
true-to-life skin texture with natural imperfections, muted naturalistic color, fine film grain, subtle
handheld camera movement, natural motion blur, shallow realistic depth of field, plain unbranded props.
Photoreal, not glossy, not CGI, not an advertisement. No on-screen text, no captions, no watermark, no
logos.`

Max realism/consistency upgrade: generate a photoreal still first (Imagen/Nano Banana, documentary-photo
language) and use it as Veo's **first-frame image** (image→video), then animate. Locks the look + character.

V1 (cold open) and V2 (anxiety) are keepers as-is. Re-roll V3–V7 with the realism block; keep the
warm-glow-from-screen unreadable so we composite the real card in the edit.

**Intercut these from the REAL extension (screen-capture, NOT Veo) — the winning beats:** card
slide-in + fold-to-seal · restraint (neutral msg → silence) · safety (crisis → help card, blurred) ·
memory ("returned to anxiety 4× lately") · MCP (same engine in VS Code + phone-width chatgpt.com).

---

## REEL 1 — "in due season we shall reap" (Galatians 6:9)
9:16 · ~10s · photoreal · reverent. If the model caps at ~5s, generate as **1A + 1B** and cut on the
season turn.

**Shot 1A (0–5s) — sowing in hardship**
> Cinematic vertical 9:16, photorealistic. A weathered farmer in simple linen work clothes walks a
> muddy furrowed field under a grey wind-driven sky, scattering seed by hand; fine rain flecks the
> air. Slow dolly that follows him from the side, shallow depth of field, soft overcast light,
> earthy muted palette of brown and slate. Quiet determination on his face. Film grain, 24fps.

**Shot 1B (5–10s) — the season turns to harvest**
> Cinematic vertical 9:16, photorealistic. Slow time-lapse dissolve of the SAME field turning golden
> under warm low evening sun; tall ripe wheat sways in the wind. The farmer stands among the golden
> harvest, weathered hands brushing the grain, calm resolve on his face. Warm honeyed light, gentle
> haze, reverent stillness. Film grain, 24fps.

Reel VO over this (Isabella preset): *"…in due season, we shall reap."*

---

## REEL 2 — "your heavenly Father feedeth them" (Matthew 6:26/34)
9:16 · ~8–10s · photoreal · peaceful.

> Cinematic vertical 9:16, photorealistic. A flock of small birds lifts and wheels over a dew-soft
> meadow at first light; low mist drifts over the grass; the sun breaks gold on the horizon. Slow
> upward camera tilt following the birds into the brightening sky; gentle weightless motion; warm
> dawn palette, soft haze, restrained lens flare. Peaceful, reverent, breath-like pacing. Film
> grain, 24fps.

Reel VO over this (Isabella preset): *"…your heavenly Father feedeth them."*

---

## SCENARIO B-ROLL (realistic people — you have no actors, so generate these)
16:9, photoreal, warm cinematic grade, faces allowed, no text. ~4–6s each; the film cuts around them.

**A — the heavy evening (adult, ~30s)**
> Photorealistic, 16:9. A dim room late at night; a tired adult in their early thirties sits lit
> only by a laptop screen, the cool glow on their weary face, faint reflection of the screen in
> their eyes. Very slow push-in, shallow depth of field, moody warm-to-cool contrast, quiet
> stillness. Film grain, 24fps.

**B — the exam week (student, early 20s)**
> Photorealistic, 16:9. A student in their early twenties at a cluttered desk at 2am: stacks of
> books, an energy drink, a laptop with many glowing tabs. They rub tired eyes, anxious restless
> energy. Subtle handheld micro-movement, warm desk-lamp key light against cool night window. Film
> grain, 24fps.

**Connective B-roll (any free tier is fine):** close-up of hands, a dark night room, pages of a
book turning, first light through a window at dawn. Warm and relatable.

---

## Voices (free, real, in-repo) — capture from the engine, don't fake
Run the engine, then pull WAVs (see `VIDEO-SCRIPT.md` capture checklist):
- George (deep, chapel-quiet) — Galatians 6:9:
  `http://127.0.0.1:8765/tts?voice=george&text=And%20let%20us%20not%20be%20weary%20in%20well%20doing...`
- Bella (auto-read) — Matthew 6:34: `?voice=bella&text=Take%20therefore%20no%20thought%20for%20the%20morrow...`
- Isabella (reel VO) — the two reel lines above.
Pick winners in `data/voice-lab/index.html`. Inner-voice narration: record dry and close, duck music under it.

---

## Assembly (ffmpeg) — free
1. Screen-capture the **live** extension on chatgpt.com (`RESONATE_MODE=live`): slide-in, fold-to-seal,
   unfold, dismiss, safety card, memory line. (Keys opened 2026-07-06, so verse text is real now.)
2. Drop finished reel files/links into `data/reels.json` so the in-film button opens YOUR reel.
3. Layer: screen-capture + scenario B-roll + reels + Kokoro VO + soft ambient piano (swell once at
   ~2:05). Hold the fold-to-seal and the reel-tap an extra half-second each.
4. End card: RESONATE wordmark on parchment — paper `#efe9df`, ink `#211d17`, clay `#a65b43`.
   Footer: "Powered by YouVersion Platform + Gloo AI Studio".
5. Export 1080p (reels 1080×1920, film 1920×1080), YouTube, under 3:00.

## Guardrails
- Everything shown must be real. If a shot isn't ready, **cut it — never mock it.**
- Reels are clearly the generated "story" format, labeled as hosted on YouVersion / a partner — not
  presented as Scripture itself.
- Protect the restraint beat (neutral message → silence) and the safety beat (crisis → help card).
