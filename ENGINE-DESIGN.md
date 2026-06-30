# Resonate — Context Engine Design (v2)

**Resonate is a personalized, verified, safety-gated Scripture retrieval engine with a
temporal memory graph.** It sits between the two required APIs and answers one hard question:
*which verse, for this exact moment, for this specific person, right now — and is it true,
safe, and not a repeat?*

```
        Gloo AI Studio                 Resonate Engine                      YouVersion
       (understanding)                 (the matchmaker)                    (verified text)
       ----------------                ----------------                    --------------
 raw text ─► segment ─► beats ─► encode ─► HYBRID RETRIEVE ─► MEMORY RE-RANK ─► LLM VERIFY ─► SAFETY ─► fetch ─► bridge ─► deliver
                                     (dense+BM25+tags,            │  (Gloo, constrained)              (YouVersion)   (Gloo)      │
                                      fused with RRF)             │                                                             │
                                                                  └──────────── per-user CONTEXT GRAPH (beats↔themes↔verses, over time) ◄──────┘
```

**Division of labour — the pitch for "innovative use of both APIs":**
- **Gloo AI = understanding + language.** Reads messy human text → structured emotion/theme
  JSON; later picks the best candidate *with a rationale* (constrained to our vetted set),
  writes the human bridge sentence, and runs the safety check. **It never quotes Scripture.**
- **YouVersion = ground truth.** Every verse the user sees is fetched live by reference, in
  the creator's chosen translation/language. The LLM proposes; YouVersion provides.
- **The Engine (our IP) = everything in between** — hybrid retrieval, a temporal memory
  graph, the fusion + re-ranking math, confidence/abstention, and evaluation. This is the
  part nobody has shipped, and it's what wins Technical Depth.

> **Reality check (kept honest on purpose).** No entry is *guaranteed* to win — execution,
> story, and the video decide it. This design is built to max out all three rubric categories
> and to be impossible to dismiss as "faked." Protect demo + video time accordingly.

---

## The pipeline, stage by stage

### 1. Ingest & segment  *(Gloo, structured output)*
Input: any text — a podcast/video transcript (with timestamps), a journal entry, a sentence.
Gloo returns JSON "beats":
```json
{ "timestamp": "14:32", "text": "...I just feel like I'm failing everyone",
  "themes": ["weariness","doubt"], "emotion": "discouragement", "intensity": 0.82 }
```
`themes` are constrained to a controlled vocabulary (see `data/verses.json`) so they line up
with how the verses are tagged. Structured output makes everything downstream computable and
explainable.

### 2. Encode  *(ML — dense embeddings)*
Embed each beat with a sentence-transformer (`all-MiniLM-L6-v2` by default — free, offline,
notebook-friendly). Verse embeddings are precomputed once from each verse's tags/keywords/
pastoral note (never the verse text — that's fetched live). v0 ships a dependency-free
TF-IDF embedder behind the same interface so the engine runs before any model is installed.

### 3. Hybrid retrieval + RRF  *(ML — the state-of-the-art part)*
Three independent retrievers each rank the verse shortlist for a beat:
- **Dense / semantic** — cosine(beat_vector, verse_vector). Catches meaning even when no
  keyword matches ("I can't keep going" ↔ a perseverance verse).
- **Sparse / lexical** — BM25 over the verse profiles. Catches exact, rare, high-signal words.
- **Theme-tag** — overlap of the beat's themes with each verse's tags.

The three ranked lists are fused with **Reciprocal Rank Fusion**:
```
RRF(v) = Σ_retrievers  1 / (k + rank_r(v))         # k ≈ 60
```
RRF is robust because it needs no score calibration across retrievers — it only uses ranks.
Keep the top-K (≈12) fused candidates. *(This is the technique GitNexus uses; we implement it
ourselves in ~15 lines — no heavy graph DB, no noncommercial-license baggage.)*

### 4. Memory re-rank  *(the temporal context graph — what makes it "living")*
Adjust the fused candidates using the per-user context graph (next section):
```
final(v) =  w_rrf  * norm(RRF)                # base hybrid relevance
          + w_tone * tone_fit(intensity, v)   # right posture for the moment
          − w_recent * recently_used(v)       # memory: don't repeat a verse
          − w_repeat * theme_fatigue(theme)   # memory: don't hammer one theme
          + w_arc  * narrative_continuity(v)  # memory: continue their journey
```
- **tone_fit** is the human subtlety: a high-intensity grief beat (0.85) gets a *comfort*
  verse, **not** a *challenge* verse ("rejoice always!"). Each verse declares an
  `intensity_fit` range + a `tone`.
- the three **memory** terms turn a one-shot lookup into a relationship that remembers.

### 5. LLM verify / select  *(Gloo, constrained — anti-hallucination)*
Hand Gloo the beat + the top fused/re-ranked candidates (references + notes only) and ask it
to **pick the single best fit and justify it in one line — choosing only from this list, or
returning `none`.** This gives the nuance of an LLM *without* letting it freelance Scripture:
it can't invent a reference, only choose from a vetted set. If it returns `none`, we abstain
(stage 7).

### 6. Safety gate  *(Gloo guardrails + classifier backstop)*
Before delivery, classify the beat for crisis / self-harm / abuse signals. If hit → **do not
auto-deliver a verse.** Surface a gentle "this might need a person, not a verse" card with
real help resources. Cheap to build; it's exactly the thoughtfulness judges are told to look
for, and it protects real people.

### 7. Confidence & abstention
If the top final score is below threshold, or the top two candidates are within ε (the engine
is "unsure"), Resonate softens — a gentler general verse, or no verse — rather than forcing a
bad match. Calibrated humility reads as maturity and prevents the demo-killing tone-deaf hit.

### 8. Verified fetch  *(YouVersion)*
Fetch the winning verse's `usfm` reference in the creator's translation/language.
**This is the only source of verse text in the entire system.**

### 9. Bridge  *(Gloo, second pass)*
One sentence linking the person's *actual words* → the verse, so it feels native, not bolted
on. Generated in the target language for multilingual delivery. Optional text-to-speech.

### 10. Remember  *(write to the context graph)*
Append the delivery as edges/nodes in the user's graph and update pattern stats — feeding
stages 4 and the series-memory feature.

---

## The per-user context graph (memory)
A small, owned, explainable graph — no external database required (in-memory + JSON/SQLite
persistence; swappable for a real graph DB later).

```
(User)──HAS──►(Episode)──CONTAINS──►(Beat)──EXPRESSES[intensity]──►(Theme)
                                       │                               ▲
                                       └──RECEIVED[timestamp]──►(Verse)─┘ ANSWERED_BY (from curated tags)
```

What the graph buys us:
- **recency / repetition** — recent `RECEIVED` edges drive the no-repeat penalty.
- **theme fatigue** — count of `EXPRESSES` edges per theme in a window.
- **narrative continuity** — traverse to the user's top recurring themes; reward candidates
  that continue (or help *resolve*) an ongoing arc.
- **series memory** — *"you've returned to anxiety + provision 4 times this month"* → an
  insight panel, and the data to auto-cut a compilation devotional from the user's own
  footage. This is the most memorable demo beat and the clearest differentiator.

## Delivery Policy — the "non-annoying" brain  *(`resonate/policy.py`)*
The brief's core demand is *"not a pop-up, not an afterthought."* Matching the right verse is
only half of that; the other half is **restraint** — knowing *when and whether* to surface at
all. The Delivery Policy is a layer between the engine (which verse) and the surface (where),
separate and independently testable. It enforces:
- **Seam-timed** — only fires on natural boundary events (a finished lesson, a real struggle,
  a milestone, a deliberate pause), never mid-flow. Mid-activity → silence.
- **Confident** — stays silent unless the match clears a confidence bar.
- **Rare = precious** — a cooldown between surfaces + a hard per-session cap.
- **Learns** — a dismissal backs that theme off for a while.
- **Manual always honoured** — if the person explicitly asks, it answers.

`scripts/policy_demo.py` simulates a study session and shows Scripture staying silent during
"typing," surfacing at the struggle, *holding one back at a valid seam because of cooldown*,
then speaking at the pause and the streak. This turns "non-annoying" from a vibe into a
measured, tested property — the moat when everyone else can also fetch a verse.

## Storage & caching layer  *(Redis-backed, with local fallback)*
The memory + retrieval layer sits behind one interface with two backends, chosen by config:
- **Local (default for dev / offline):** in-memory + JSON/SQLite persistence. Zero services,
  runs in a notebook.
- **Redis (production / scale):** the *same* interface backed by Redis — three jobs in one fast
  store:
  1. **Vector index** for verse + beat embeddings (Redis Query Engine, HNSW) → the dense
     retriever at scale.
  2. **Episodic memory** — the per-user context graph (recency, fatigue, arcs) in Redis
     structures.
  3. **Semantic cache** — cache Gloo segmentation/bridge responses keyed by embedding
     similarity, cutting latency and cost on repeat/similar inputs.

Redis never blocks the demo: if it's unavailable the engine falls back to local automatically.
A free managed tier (Redis Cloud / Upstash) covers deployment. This makes the "context is the
product" thesis (cf. Redis's talk *Context is all you need*) concrete — and gives a clean scale
story for Impact.

## Multilingual (a scale/Impact lever)
YouVersion licenses ~1,500 translations across 1,300+ languages. Gloo's reasoning is
language-agnostic, and the bridge is generated in the target language — so the *same* engine
delivers Scripture in the creator's own language. Even demoing English + one more (e.g. Hindi
or Spanish) turns "nice tool" into "could reach billions who don't read English."

## Personalization  *(stretch)*
Thumbs up / down on deliveries are logged; periodically nudge the per-user weights (a tiny
logistic re-ranker) so Resonate learns an individual creator's voice over time.

## Evaluation harness  *(proof it works — not just a demo)*
A labeled set (~40–60 context snippets with acceptable themes + gold verse references) plus:
- **Theme-F1** (segmentation quality)
- **Recall@k / Precision@1** (retrieval quality)
- **Tone-appropriateness** (LLM-as-judge, 1–5, via Gloo)
- **No-repeat rate** over a simulated multi-episode session
- **Safety recall** on a crisis test set
A metrics table in the notebook is what separates "looks like it works" from "provably works."

---

## Why this beats the naive approach
The obvious version — *"ask the LLM for a verse, show it"* — loses on every axis judges score:
| Naive (LLM freelances) | Resonate (engine) |
|---|---|
| Hallucinates references / wrong translation | Verified live fetch from YouVersion; LLM constrained to a vetted set |
| Single retriever, brittle | Hybrid dense + BM25 + tags, fused with RRF |
| No memory — repeats, ignores history | Temporal context graph: recency, fatigue, narrative arcs |
| Opaque — "trust me" | Transparent fit score + LLM rationale, inspectable |
| No tone control | tone_fit matches posture to intensity |
| Over-confident always answers | Confidence + abstention |
| No safety | Crisis routing before delivery |
| "Looks like it works" | Eval harness with real metrics |

---

## Build status / mock vs. live
- Competition keys open **2026-07-06**. Until then everything external is behind a pluggable
  adapter: `gloo` and `youversion` providers each have a **mock** and a **live**
  implementation chosen by config. Engine, retrieval, memory graph, eval, and UI are fully
  buildable and testable now on local embeddings + mock providers; switching to real keys is a
  one-line config change.
- The curated verse shortlist (`data/verses.json`) stores references + tags only — **never
  verse text** (fetched live; anti-hallucination + licensing).
