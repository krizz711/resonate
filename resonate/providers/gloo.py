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
    "guilt": ["guilt", "guilty", "ashamed", "shame", "regret", "i failed", "messed up", "my fault"],
    "anger": ["angry", "anger", "furious", "resentful", "bitter", "frustrated"],
    "weariness": ["tired", "tiredness", "exhausted", "weary", "burnout", "burned out", "drained", "worn out", "can't keep going"],
    "gratitude": ["grateful", "thankful", "blessed", "appreciate"],
    "joy": ["happy", "joy", "joyful", "excited", "thrilled", "glad"],
    "hope": ["hope", "hopeful", "looking forward", "better days"],
    "peace": ["peace", "calm", "peaceful", "at rest"],
    "perseverance": ["keep going", "persevere", "persist", "push through", "give up", "endure", "grind", "not give up"],
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

CRISIS = [
    "kill myself", "killing myself", "end my life", "ending my life", "suicide", "suicidal",
    "want to die", "don't want to live", "dont want to live", "no reason to live",
    "hurt myself", "harm myself", "self harm", "self-harm",
]

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
            crisis = any(p in low for p in CRISIS)
            if not scores and not crisis:
                continue
            if scores:
                themes = [t for t, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]]
                emotion, inten = EMOTION.get(themes[0], themes[0]), _intensity(s)
            else:  # crisis sentence with no theme hit — still create a beat so safety() catches it
                themes, emotion, inten = ["comfort"], "in distress", 0.95
            beats.append(Beat(index=idx, text=s, themes=themes, emotion=emotion, intensity=inten))
            idx += 1
        if not beats and text.strip():
            beats.append(Beat(index=0, text=text.strip(), themes=["hope"], emotion="reflective", intensity=0.5))
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

    def safety(self, beat):
        s = beat.text.lower()
        return any(p in s for p in CRISIS)


class LiveGloo:
    """Real Gloo AI Studio integration (OpenAI-compatible). Not exercised in mock mode;
    wired up and confirmed in Phase 1 once an API key exists."""

    def __init__(self, config):
        self.config = config

    def _chat(self, system, user, temperature=0.3):
        import httpx
        headers = {"Authorization": "Bearer %s" % self.config.gloo_api_key, "Content-Type": "application/json"}
        payload = {"model": self.config.gloo_model,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                   "temperature": temperature}
        r = httpx.post("%s/chat/completions" % self.config.gloo_base_url, headers=headers, json=payload, timeout=60)
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

    def safety(self, beat):
        # keyword backstop + (optionally) a Gloo guardrail classification call
        return any(p in beat.text.lower() for p in CRISIS)
