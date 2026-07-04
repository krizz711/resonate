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
    "grief": ["grief", "grieving", "loss", "passed away", "died", "death", "mourning", "heartbroken"],
    "loneliness": ["lonely", "alone", "isolated", "nobody", "by myself", "no one"],
    "doubt": ["doubt", "unsure", "questioning", "confused", "even matters", "pointless", "what's the point", "shouting into the void"],
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
    "comfort": ["hurting", "in pain", "aching", "suffering"],
    "courage": ["courage", "brave", "bold", "step out"],
    "rest": ["need a break", "slow down", "restless", "can't sleep"],
    "identity": ["worthless", "not enough", "not good enough", "my worth", "who i am"],
    "trust": ["trust", "rely on", "depend on", "surrender", "let go"],
    "prayer": ["pray", "prayer", "praying"],
}

EMOTION = {
    "anxiety": "anxious", "fear": "afraid", "grief": "grieving", "loneliness": "lonely",
    "doubt": "uncertain", "guilt": "weighed down", "anger": "frustrated", "weariness": "exhausted",
    "gratitude": "grateful", "joy": "joyful", "hope": "hopeful", "peace": "unsettled",
    "perseverance": "determined", "purpose": "searching", "provision": "stretched",
    "forgiveness": "remorseful", "love": "longing", "comfort": "hurting", "courage": "hesitant",
    "rest": "restless", "identity": "unsure of your worth", "trust": "holding on", "prayer": "reaching out",
}

# Crisis detection as a robust regex (handles "don't"/"do not" variants, -ing forms, etc.).
# Checked on the RAW text independently of theme segmentation, so a crisis is never missed.
_CRISIS_RE = re.compile(
    r"(?:\b(?:do\s*n[o']?t|never|no\s+longer|stop)\s+want(?:ing)?\s+to\s+(?:live|be\s+here|exist|wake\s+up)\b)"
    r"|(?:\b(?:want|wanna|going|plan(?:ning)?)\s+to\s+(?:die|kill\s+myself|end\s+(?:it\s+all|it|my\s+life|things))\b)"
    r"|(?:\b(?:kill|hurt|harm|cut)(?:ing)?\s+myself\b)"
    r"|(?:\b(?:end|ending|take|taking)\s+my(?:\s+own)?\s+life\b)"
    r"|(?:\bself[\s-]?harm\b)"
    r"|(?:\b(?:better\s+off\s+dead|no\s+reason\s+to\s+live|suicidal|suicide)\b)",
    re.IGNORECASE,
)


def is_crisis(text):
    return bool(_CRISIS_RE.search(text or ""))

_INTENSITY_CUES = ["so ", "really", "completely", "totally", "can't", "cant", "never",
                   "always", "everyone", "no one", "nobody", "every", "nothing", "honestly"]


def _intensity(sentence: str) -> float:
    s = sentence.lower()
    score = 0.4
    for c in _INTENSITY_CUES:
        if c in s:
            score += 0.07
    score += 0.06 * s.count("!")
    score += 0.07 * sum(1 for w in sentence.split() if len(w) > 2 and w.isupper())
    return max(0.2, min(0.97, score))


class MockGloo:
    def __init__(self, config):
        self.config = config

    def segment(self, text):
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

    def _chat(self, system, user, temperature=0.3):
        import httpx
        headers = {"Authorization": "Bearer %s" % self._access_token(),
                   "Content-Type": "application/json"}
        payload = {"messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}],
                   "temperature": temperature, "max_tokens": 500}
        if self.config.gloo_model:
            payload["model"] = self.config.gloo_model
        else:
            payload["auto_routing"] = True
        if self.config.gloo_tradition:
            payload["tradition"] = self.config.gloo_tradition
        r = httpx.post("%s/ai/v2/chat/completions" % self.config.gloo_base_url,
                       headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def segment(self, text):
        import json
        sys_p = ("You segment text into emotional/thematic beats. Return ONLY JSON: a list of "
                 '{"text","themes","emotion","intensity"} where themes use this vocabulary: '
                 + ", ".join(LEXICON.keys()) + ". intensity is 0..1.")
        raw = self._chat(sys_p, text)
        data = json.loads(raw[raw.find("["):raw.rfind("]") + 1])
        return [Beat(index=i, text=b["text"], themes=b.get("themes", []),
                     emotion=b.get("emotion", ""), intensity=float(b.get("intensity", 0.5)))
                for i, b in enumerate(data)]

    def verify(self, beat, candidates):
        import json
        listing = "\n".join("%d. %s — %s" % (i, c["reference"], c.get("note", "")) for i, c in enumerate(candidates))
        sys_p = ('Pick the single best verse for the beat from the numbered list ONLY. '
                 'Return JSON {"choice": <index>, "rationale": "<one sentence>"}. '
                 'If none fit, choice = -1.')
        raw = self._chat(sys_p, 'Beat: "%s" (emotion=%s)\nCandidates:\n%s' % (beat.text, beat.emotion, listing))
        obj = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        i = obj.get("choice", 0)
        chosen = candidates[i] if 0 <= i < len(candidates) else candidates[0]
        return chosen, obj.get("rationale", "")

    def bridge(self, beat, verse, verse_text):
        sys_p = "Write ONE warm sentence linking the person's words to the verse. No preamble."
        return self._chat(sys_p, 'Their words: "%s"\nVerse %s: "%s"' % (beat.text, verse["reference"], verse_text)).strip()

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
        return self._chat(sys_p, user, temperature=0.6).strip()

    def safety(self, beat):
        # regex backstop + (optionally) a Gloo guardrail classification call
        return is_crisis(beat.text)

    def safety_text(self, text):
        return is_crisis(text)
