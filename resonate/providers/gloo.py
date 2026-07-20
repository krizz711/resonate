"""Gloo AI Studio provider.

MockGloo runs offline with a transparent, rule-based stand-in for each of Gloo's jobs so the
whole engine is testable before competition keys exist (2026-07-06). LiveGloo is the real
OpenAI-compatible integration, exercised when provider_mode == "live".

Gloo's four jobs in this system:
  segment(text)             -> list[Beat]                 (stage 1)
  verify(beat, candidates)  -> (chosen_verse, rationale)  (stage 5, constrained to the list)
  bridge(beat, verse, text) -> str                        (stage 9)
  safety(beat)              -> bool (True = crisis hold)   (stage 6)
"""
from __future__ import annotations

import re

from ..models import Beat

# Controlled-vocabulary trigger lexicon (mock stand-in for Gloo's emotion/theme tagging).
LEXICON = {
    "anxiety": ["worry", "worried", "anxious", "anxiety", "stress", "stressed", "overwhelmed", "panic", "nervous", "on edge"],
    "fear": ["afraid", "fear", "scared", "terrified", "fearful", "dread"],
    # "dying" ships only as phrases — bare "dying" would false-trigger on the idiom
    # "dying to see/try..." (an excited message must never get a grief verse)
    "grief": ["grief", "grieving", "loss", "passed away", "died", "death", "mourning", "heartbroken",
              "is dying", "the dying", "dying of", "my dying", "deathbed", "hospice",
              "terminally ill", "terminal illness", "close to death", "about to die"],
    "loneliness": ["lonely", "alone", "isolated", "nobody", "by myself", "no one"],
    "doubt": ["doubt", "unsure", "questioning", "confused", "even matters", "pointless", "what's the point", "shouting into the void"],
    # overconfidence is NOT doubt — before this theme existed, "I'm the smartest one
    # here" fell onto the doubt axis (nearest neighbour, wrong pole; observed live)
    "pride": ["overconfident", "arrogant", "arrogance", "cocky", "smartest", "smarter than everyone",
              "know it all", "know-it-all", "i know everything", "better than everyone", "only smart",
              "everyone else is stupid", "world is stupid", "full of myself", "my ego",
              "im always right", "i'm always right", "wise in my own eyes"],
    # plain sadness/depression is its own axis — it is NOT grief (loss) and NOT
    # weariness (exhaustion); "im so depressed" went unanswered before this existed
    "sadness": ["sad", "depressed", "depression", "unhappy", "miserable", "feeling down",
                "feeling low", "down lately", "hopeless", "empty inside", "numb",
                "crying", "can't stop crying", "cant stop crying"],
    "envy": ["jealous", "jealousy", "envy", "envious", "wish i had their", "why do they get",
             "everyone else has", "comparing myself"],
    "betrayal": ["betrayed", "betrayal", "stabbed me in the back", "behind my back", "backstabbed",
                 "cheated on me", "turned on me", "two-faced", "lied to me"],
    "temptation": ["tempted", "temptation", "can't resist", "cant resist", "keep giving in",
                   "relapse", "relapsed", "struggling not to", "the same sin"],
    "guilt": ["guilt", "guilty", "ashamed", "shame", "regret", "i failed", "messed up", "my fault",
              "failing everyone", "let everyone down", "letting everyone down", "let them down"],
    "anger": ["angry", "anger", "furious", "resentful", "bitter", "frustrated"],
    "weariness": ["tired", "tiredness", "exhausted", "weary", "burnout", "burned out", "drained",
                  "worn out", "can't keep going", "can't keep up", "cant keep up", "cannot keep up",
                  "falling behind", "overwhelmed", "too much"],
    "gratitude": ["grateful", "thankful", "blessed", "appreciate"],
    "joy": ["happy", "joy", "joyful", "excited", "thrilled", "glad"],
    "hope": ["hope", "hopeful", "looking forward", "better days"],
    "peace": ["peace", "calm", "peaceful", "at rest"],
    "perseverance": ["keep going", "kept going", "persevere", "persist", "push through", "give up",
                     "giving up", "endure", "grind", "not give up", "stuck", "can't fix",
                     "debugging", "not working", "keep trying"],
    "purpose": ["purpose", "calling", "meaning", "why am i here", "made for", "matters"],
    "provision": ["money", "bills", "afford", "provide", "provision", "rent", "paycheck"],
    "forgiveness": ["forgive", "forgiven", "forgiveness", "repent"],
    "love": ["unloved", "loved", "longing"],
    # asking for comfort IS a comfort beat ("any words that can comfort me?") — phrases
    # only, so "comfortable chairs" stays silent
    "comfort": ["hurting", "in pain", "aching", "suffering", "comfort me", "comfort myself",
                "need comfort", "any comfort", "comforting", "be comforted", "words of comfort"],
    "courage": ["courage", "brave", "bold", "step out"],
    "rest": ["need a break", "slow down", "restless", "can't sleep"],
    "identity": ["worthless", "not enough", "not good enough", "my worth", "who i am"],
    "trust": ["trust", "rely on", "depend on", "surrender", "let go"],
    "prayer": ["pray", "prayer", "praying"],
}

EMOTION = {
    "anxiety": "anxious", "fear": "afraid", "grief": "grieving", "loneliness": "lonely",
    "doubt": "uncertain", "pride": "self-assured", "sadness": "downcast", "envy": "envious",
    "betrayal": "wounded",
    "temptation": "pulled", "guilt": "weighed down", "anger": "frustrated", "weariness": "exhausted",
    "gratitude": "grateful", "joy": "joyful", "hope": "hopeful", "peace": "unsettled",
    "perseverance": "determined", "purpose": "searching", "provision": "stretched",
    "forgiveness": "remorseful", "love": "longing", "comfort": "hurting", "courage": "hesitant",
    "rest": "restless", "identity": "unsure of your worth", "trust": "holding on", "prayer": "reaching out",
}

# Crisis detection as a robust regex (handles "don't"/"do not" variants, -ing forms, etc.).
# Checked on the RAW text independently of theme segmentation, so a crisis is never missed.
_CRISIS_RE = re.compile(
    r"(?:\b(?:do\s*n[o']?t|never|no\s+longer|stop|can[o']?t)\s+(?:want(?:ing)?\s+to|wanna)\s+"
    r"(?:live|be\s+here|be\s+alive|stay\s+alive|exist|wake\s+up)\b)"
    r"|(?:\b(?:want|wanna|going|plan(?:ning)?)\s+to\s+"
    r"(?:die|be\s+dead|kill\s+myself|end\s+(?:it\s+all|it|my\s+life|things))\b)"
    r"|(?:\b(?:kill|hurt|harm|cut)(?:ing)?\s+myself\b)"
    r"|(?:\b(?:end|ending|take|taking)\s+my(?:\s+own)?\s+life\b)"
    r"|(?:\bself[\s-]?harm\b)"
    r"|(?:\b(?:better\s+off\s+(?:dead|gone)|no\s+reason\s+to\s+(?:live|be\s+here|go\s+on)|"
    r"do\s*n[o']?t\s+want\s+to\s+be\s+alive|suicidal|suicide|want\s+to\s+disappear)\b)"
    # Common real-world phrasings the first pass missed — indirect/passive ideation, method-
    # specific, slang, contractions, a few non-English stems. Validated at 0 false positives
    # against a benign battery incl. "wish I was taller", "isn't worth reading", "overdosed on
    # caffeine", "never wake up on time", "jumping off the diving board", "I miss my best friend".
    # Recall matters more than precision for a safety gate: a false catch is a help card instead
    # of a verse (safe); a miss shows Scripture to someone in crisis (harm).
    r"|(?:\bwish\s+i\s+(?:was|were)\s+dead\b)"
    r"|(?:\bwish\s+i\s+(?:wasn'?t|weren'?t|was\s+not|were\s+not)\s+(?:alive|here|born)\b)"
    r"|(?:\bwish\s+i\s+(?:had\s+)?(?:never|hadn'?t\s+(?:ever\s+)?)\s*(?:been\s+)?born\b)"
    r"|(?:\b(?:not|isn'?t|ain'?t|aren'?t|nothing|no\s+longer|never|hardly)\b[^.!?;]{0,15}\bworth\s+living\b)"
    r"|(?:\bslit(?:ting|s|ted)?\s+(?:my|his|her|the|their)?\s*wrist)"
    r"|(?:\boverdos(?:e|ing|ed)\s+on\s+(?:my\s+|the\s+|these\s+)?(?:pills|meds|medication|tablets|drugs)\b"
    r"|\btak(?:e|ing)\s+all\s+(?:my|these|the)\s+pills\b|\btake\s+an?\s+overdose\b|\bwant\s+to\s+overdose\b)"
    r"|(?:\bsleep\s+and\s+never\s+wake\s+up\b|\bnever\s+wake\s+up\s+again\b)"
    r"|(?:\bbetter\s+off\s+without\s+me\b)"
    r"|(?:\b(?:nobody|no\s+one|no-one)\s+(?:would|will|'?d)\s+(?:even\s+)?miss\s+me\b)"
    r"|(?:\bwhat'?s\s+the\s+point\s+of\s+(?:living|life|it\s+all|going\s+on|anything)\b)"
    r"|(?:\bno\s+(?:point|sense|reason)\s+(?:in\s+)?(?:being\s+alive|to\s+live|going\s+on|carrying\s+on|to\s+be\s+here)\b)"
    r"|(?:\bjump(?:ing)?\s+off\s+(?:a|the)\s+(?:bridge|building|roof|balcony)\b)"
    r"|(?:\bwant\s+(?:to\s+get\s+)?out\s+of\s+(?:this\s+)?life\b)"
    r"|(?:\bwant\s+to\s+not\s+(?:exist|be\s+here|be\s+alive|wake\s+up)\b)"
    r"|(?:\bunaliv(?:e|ed|ing)\b)"
    r"|(?:\bquiero\s+morir\b|\bno\s+quiero\s+vivir\b|\bquiero\s+matarme\b)"
    r"|(?:\bthoughts?\s+of\s+(?:not\s+being\s+here|not\s+existing|ending\s+it|ending\s+things|dying|suicide|self[\s-]?harm)\b)",
    re.IGNORECASE,
)


def is_crisis(text):
    return bool(_CRISIS_RE.search(text or ""))

_INTENSITY_CUES = ["so ", "really", "completely", "totally", "can't", "cant", "never",
                   "always", "everyone", "no one", "nobody", "every", "nothing", "honestly"]

# Objectively heavy life events read as high-intensity even when stated flatly —
# "My dad died last week." carries no amplifier words, but a comfort-tone verse
# (intensity_fit floor 0.6) must not lose to a brighter one because the sentence
# was quiet. Grief speaks quietly.
_GRAVITY_CUES = ["died", "death", "passed away", "passed", "funeral", "buried", "grave",
                 "mourning", "grieving", "grief", "loss of", "lost my", "lost her", "lost him",
                 "miscarriage", "stillborn", "terminal", "hospice", "cancer",
                 "diagnos", "divorce", "abuse", "assault", "barely breathe"]


def _intensity(sentence: str) -> float:
    s = sentence.lower()
    score = 0.4
    for c in _INTENSITY_CUES:
        if c in s:
            score += 0.07
    score += 0.06 * s.count("!")
    score += 0.07 * sum(1 for w in sentence.split() if len(w) > 2 and w.isupper())
    if any(c in s for c in _GRAVITY_CUES):
        score = max(score, 0.72)
    return max(0.2, min(0.97, score))


def lexicon_segment(text):
    """Rule-based beat segmentation. MockGloo's stage 1, and LiveGloo's safety net when
    a live model answers with prose instead of JSON — the pipeline never breaks on it."""
    beats, idx = [], 0
    for s in [p.strip() for p in re.split(r"(?<=[.!?])\s+|\n+", text) if p.strip()]:
        low = s.lower()
        scores = {}
        for theme, phrases in LEXICON.items():
            hits = sum(1 for p in phrases if p in low)
            if hits:
                scores[theme] = hits
        crisis = is_crisis(s)
        if not scores and not crisis:
            continue
        if scores:
            themes = [t for t, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]]
            emotion, inten = EMOTION.get(themes[0], themes[0]), _intensity(s)
        else:  # crisis sentence with no theme hit — still create a beat so safety() catches it
            themes, emotion, inten = ["comfort"], "in distress", 0.95
        beats.append(Beat(index=idx, text=s, themes=themes, emotion=emotion, intensity=inten))
        idx += 1
    # No emotional/thematic beat -> return nothing. The engine stays silent rather than
    # manufacturing a verse for non-resonant text ("only speaks when it hears a story").
    return beats


def _json_array(raw):
    """Pull a JSON array out of a model reply that may carry fences, prose, or a wrapper object."""
    import json
    s = (raw or "").strip()
    if s.startswith("```"):
        s = s.strip("`")
        if "\n" in s:  # drop a possible language tag line ("json")
            s = s.split("\n", 1)[1]
    i, j = s.find("["), s.rfind("]")
    if i >= 0 and j > i:
        return json.loads(s[i:j + 1])
    obj = json.loads(s[s.find("{"):s.rfind("}") + 1])
    for k in ("beats", "segments", "items", "data"):
        if isinstance(obj.get(k), list):
            return obj[k]
    raise ValueError("no JSON array in model output")


def template_bridge(beat, verse):
    """Tone-matched one-liner linking the person's words to the verse. The mock's
    bridge, and the live provider's safety net when the network drops mid-request —
    a plainer sentence beats a dropped connection."""
    snippet = beat.text.strip()
    if len(snippet) > 80:
        snippet = snippet[:77] + "..."
    ref = verse["reference"]
    templates = {
        "comfort": 'When you said "%s", you don\'t have to carry it alone — %s meets you right there.' % (snippet, ref),
        "assurance": 'You said "%s". Hold onto this: %s.' % (snippet, ref),
        "hope": 'After "%s", here\'s something to hold onto: %s.' % (snippet, ref),
        "challenge": 'You said "%s". A nudge to keep going: %s.' % (snippet, ref),
        "celebration": '"%s" — worth celebrating with %s.' % (snippet, ref),
        "conviction": '"%s" — a gentle truth to sit with: %s.' % (snippet, ref),
    }
    return templates.get(verse.get("tone", "hope"), templates["hope"])


class MockGloo:
    def __init__(self, config):
        self.config = config

    def segment(self, text):
        return lexicon_segment(text)

    def verify(self, beat, candidates):
        """Constrained selection: choose the best verse from the provided shortlist only.
        (Live Gloo re-evaluates with the LLM; mock trusts the engine's ranking and explains it.)"""
        chosen = candidates[0]
        snippet = beat.text.strip()
        if len(snippet) > 70:
            snippet = snippet[:67] + "..."
        rationale = ('Chose from %d vetted candidates — best fit for the %s in "%s": %s'
                     % (len(candidates), beat.emotion, snippet, chosen.get("note", "")))
        return chosen, rationale

    def bridge(self, beat, verse, verse_text):
        return template_bridge(beat, verse)

    def story(self, user_text, emotion, narrative, verse, memory_note=None):
        """Mock 'Your story': an honest template that mirrors the user's words, retells
        the vetted narrative's synopsis, and hands off to the verified verse. Live Gloo
        writes this properly; the mock proves the shape offline."""
        snippet = (user_text or "").strip()
        if len(snippet) > 90:
            snippet = snippet[:87] + "..."
        parts = [
            'You said "%s" — and you are not the first to stand exactly there.' % snippet,
            "%s: %s" % (narrative["title"], narrative["synopsis"]),
        ]
        if memory_note:
            parts.append("This keeps finding you lately — %s That's not failure; that's a thread." % memory_note.lower())
        parts.append("Which is why these words were kept for a moment like yours — %s: “%s”"
                     % (verse.get("reference", ""), (verse.get("verse_text", "") or "").strip()))
        return "\n\n".join(parts)

    def converse(self, system, messages, temperature=0.55, max_tokens=420):
        """Mock Scripture Guide turn: mirror the question and hand back the grounded
        verse from the CONTEXT block (never invented) — proves the shape offline."""
        last = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        snippet = last.strip()
        if len(snippet) > 70:
            snippet = snippet[:67] + "..."
        ctx = system.split("CONTEXT:\n", 1)[-1].strip()
        if ctx and ctx != "(empty)":
            first = ctx.splitlines()[0]
            return ('Sitting with "%s" — here is where Scripture meets it. %s '
                    "Would you like to stay with this verse, or look at its story?"
                    % (snippet, first))
        return ('You asked "%s". Let\'s walk through what the Scriptures say about it '
                "together — tell me a little more of where this question comes from."
                % snippet)

    def safety(self, beat):
        return is_crisis(beat.text)

    def safety_text(self, text):
        return is_crisis(text)


class LiveGloo:
    """Real Gloo AI Studio integration, per docs.gloo.com (verified 2026-07-04):

      auth : OAuth2 client-credentials — POST {base}/oauth2/token with
             Basic base64(client_id:client_secret), body
             grant_type=client_credentials&scope=api/access; tokens live 1h.
      chat : POST {base}/ai/v2/chat/completions with Bearer <access_token>;
             routing via auto_routing=true (or an explicit gloo model id) and an
             optional `tradition` (theological perspective) parameter.

    A grounded variant exists at /ai/v2/chat/completions/grounded (RAG +
    citations via rag_publisher / include_citations) — a candidate for citing
    devotional sources in bridges later; not used in the core path."""

    def __init__(self, config):
        self.config = config
        self._token = None
        self._token_exp = 0.0

    def _access_token(self):
        import base64
        import time as _time
        import httpx
        if self._token and _time.time() < self._token_exp - 300:
            return self._token
        basic = base64.b64encode(
            ("%s:%s" % (self.config.gloo_client_id, self.config.gloo_client_secret)).encode()).decode()
        r = httpx.post(
            "%s/oauth2/token" % self.config.gloo_base_url,
            headers={"Authorization": "Basic %s" % basic,
                     "Content-Type": "application/x-www-form-urlencoded"},
            content="grant_type=client_credentials&scope=api/access",
            timeout=30)
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        self._token_exp = _time.time() + float(data.get("expires_in", 3600))
        return self._token

    def _chat(self, system, user, temperature=0.3, model=None, json_mode=False):
        import httpx
        headers = {"Authorization": "Bearer %s" % self._access_token(),
                   "Content-Type": "application/json"}
        payload = {"messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}],
                   "temperature": temperature, "max_tokens": 500}
        if model or self.config.gloo_model:
            payload["model"] = model or self.config.gloo_model
        else:
            payload["auto_routing"] = True
        if json_mode:  # OpenAI-compatible structured output (verified honored 2026-07-10)
            payload["response_format"] = {"type": "json_object"}
        if self.config.gloo_tradition:
            payload["tradition"] = self.config.gloo_tradition
        r = httpx.post("%s/ai/v2/chat/completions" % self.config.gloo_base_url,
                       headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def converse(self, system, messages, temperature=0.55, max_tokens=420):
        """Multi-turn persona chat (Scripture Guide). Unlike the structured calls below,
        the alignment layer's pastoral instinct is exactly right here — we only pin
        gloo_model_guide to keep voice-call latency predictable (empty => auto_routing)."""
        import httpx
        headers = {"Authorization": "Bearer %s" % self._access_token(),
                   "Content-Type": "application/json"}
        payload = {"messages": [{"role": "system", "content": system}] + list(messages),
                   "temperature": temperature, "max_tokens": max_tokens}
        if self.config.gloo_model_guide:
            payload["model"] = self.config.gloo_model_guide
        else:
            payload["auto_routing"] = True
        if self.config.gloo_tradition:
            payload["tradition"] = self.config.gloo_tradition
        r = httpx.post("%s/ai/v2/chat/completions" % self.config.gloo_base_url,
                       headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    # Gloo's alignment layer answers emotional first-person text with pastoral care —
    # even with a model pinned, a plain "return JSON" system prompt loses (observed live
    # 2026-07-10). The recipe that holds: frame the input as third-party DATA to annotate
    # ("not addressed to you"), demand verbatim text copies, and set response_format.
    _ANNOTATOR = ("You are a text-annotation service inside a Scripture app's retrieval "
                  "pipeline. The snippet you receive is data from elsewhere, not someone "
                  "talking to you; downstream systems handle all care. You only emit "
                  "machine-readable JSON — never advice, never commentary.")

    def segment(self, text):
        import sys as _sys
        contract = ('Segment the snippet into emotional/thematic beats. Return a JSON object '
                    '{"beats": [{"text","themes","emotion","intensity"}]}. Rules: "text" is the '
                    "sentence copied VERBATIM from the snippet (never your own words); \"themes\" "
                    "use ONLY this vocabulary: " + ", ".join(LEXICON.keys()) + ' — and when a '
                    'sentence is emotional but NO listed theme truly fits, use ["other:<one-or-two-'
                    'word name of the feeling>"] (e.g. ["other:embarrassment"]); NEVER '
                    "force the nearest theme (overconfidence is not doubt); intensity is "
                    '0..1; skip sentences with no emotional/thematic content — including '
                    'difficulty understanding an academic or technical topic ("I can\'t '
                    'understand calculus"), which is study frustration, not an emotional or '
                    'spiritual moment; {"beats": []} if none.'
                    "\n\nANNOTATE THIS SNIPPET (data, not addressed to you):\n<<<%s>>>" % text)
        try:
            raw = self._chat(self._ANNOTATOR, contract,
                             model=self.config.gloo_model_structured, json_mode=True)
            data = _json_array(raw)
            return [Beat(index=i, text=b.get("text", ""), themes=b.get("themes", []),
                         emotion=b.get("emotion", ""), intensity=float(b.get("intensity", 0.5)))
                    for i, b in enumerate(data) if isinstance(b, dict)]
        except Exception as e:
            _sys.stderr.write("live segment -> lexicon fallback (%s)\n" % str(e)[:120])
            return lexicon_segment(text)

    def verify(self, beat, candidates):
        import json
        listing = "\n".join("%d. %s — %s" % (i, c["reference"], c.get("note", "")) for i, c in enumerate(candidates))
        contract = ('Pick the single best verse for the annotated beat from the numbered list ONLY. '
                    'Return a JSON object {"choice": <index>, "rationale": "<one sentence>"}; '
                    'choice = -1 if none fit.\n\nBEAT (data, not addressed to you): '
                    '<<<%s>>> (emotion=%s)\nCANDIDATES:\n%s' % (beat.text, beat.emotion, listing))
        try:
            raw = self._chat(self._ANNOTATOR, contract,
                             model=self.config.gloo_model_structured, json_mode=True)
            obj = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception:
            return candidates[0], "Top-ranked candidate (live verify output was unparseable)."
        i = obj.get("choice", 0)
        chosen = candidates[i] if 0 <= i < len(candidates) else candidates[0]
        return chosen, obj.get("rationale", "")

    def bridge(self, beat, verse, verse_text):
        sys_p = ("Write ONE warm sentence linking the person's words to the verse. "
                 "Output only that sentence — no preamble, no quotes around it.")
        try:
            return self._chat(sys_p, 'Their words: "%s"\nVerse %s: "%s"' % (beat.text, verse["reference"], verse_text),
                              temperature=0.6, model=self.config.gloo_model_structured).strip()
        except Exception as e:
            import sys as _sys
            _sys.stderr.write("live bridge -> template fallback (%s)\n" % str(e)[:120])
            return template_bridge(beat, verse)

    def story(self, user_text, emotion, narrative, verse, memory_note=None):
        sys_p = (
            "You write a short personal reflection (170-220 words, second person, warm, "
            "reverent, unhurried — never preachy, never clinical) that weaves the person's "
            "present moment into ONE given biblical narrative. HARD RULES: use ONLY the "
            "narrative provided (title, reference, synopsis) — do not import other passages; "
            "NEVER invent or quote scripture wording — the verse text is supplied and must be "
            "quoted exactly once, verbatim, at the end, introduced by its reference; make no "
            "promises of outcomes; no medical or crisis advice. Structure: (1) meet them in "
            "their own words, (2) walk them into the narrative as if standing beside it, "
            "(3) land on the supplied verse."
        )
        mem = ("\nRecurring thread: %s" % memory_note) if memory_note else ""
        user = ('Their words: "%s" (emotion: %s)%s\n\nNarrative: %s (%s)\nSynopsis: %s\n\n'
                'Verse to end on — %s (%s): "%s"'
                % (user_text, emotion, mem, narrative["title"], narrative["reference"],
                   narrative["synopsis"], verse.get("reference", ""),
                   verse.get("translation", "KJV"), verse.get("verse_text", "")))
        try:
            return self._chat(sys_p, user, temperature=0.6).strip()
        except Exception as e:
            # every other live call degrades instead of erroring — stories must too
            # (a Gloo outage mid-demo should read as a plainer story, never a 502)
            import sys as _sys
            _sys.stderr.write("live story -> template fallback (%s)\n" % str(e)[:120])
            return MockGloo(self.config).story(user_text, emotion, narrative, verse, memory_note)

    def safety(self, beat):
        # Safety is DETERMINISTIC by design — the same phrasing-robust regex in mock and live.
        # We deliberately do NOT delegate crisis detection to the LLM: a model can refuse, drift,
        # or rate-limit, and a missed crisis is the one failure this product must never have.
        return is_crisis(beat.text)

    def safety_text(self, text):
        return is_crisis(text)
