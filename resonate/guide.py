"""Scripture Guide — the conversational brain behind the chat widget and the web call.

One shared core both channels hit (POST /guide): safety gate first, then OUR retrieval
grounds the turn (hybrid RRF over the curated corpus + live YouVersion text — manual RAG,
no Data Engine subscription needed), then one Gloo chat completion answers in persona.

Guarantees, same as everywhere else in the engine:
  crisis -> the help message and a guardian alert, never a verse, never a chat answer;
  verse wording only from the provider (context block), never from model memory;
  voice turns stay short (a call needs 2-3 sentences, not a sermon).
"""
from __future__ import annotations

from .engine import SAFETY_MESSAGE
from .providers.gloo import lexicon_segment

PERSONA = (
    "You are Scripture Guide — warm, reverent, plain-spoken, and honest about hard "
    "questions and differing views. You discuss the Scriptures with people: context, "
    "meaning, history, application. HARD RULES: quote verse wording ONLY from the "
    "CONTEXT block below, verbatim, citing the reference; if the CONTEXT is empty you "
    "may discuss books, passages and themes but NEVER quote or reconstruct wording from "
    "memory. Never invent references. No promises of outcomes; no medical or legal "
    "advice. If someone sounds like they are in crisis, respond with care and human "
    "help lines, never a verse."
)


class ScriptureGuide:
    def __init__(self, engine):
        self.engine = engine

    def _ground(self, text):
        """Our retrieval as manual RAG: lexicon beats -> hybrid retrieve -> licensed text."""
        refs = []
        for beat in lexicon_segment(text)[:2]:
            for c in self.engine.retriever.retrieve(beat, topk=3)[:1]:
                v = c["verse"]
                if any(r["reference"] == v["reference"] for r in refs):
                    continue
                fetched = self.engine.yv.fetch(v["usfm"], self.engine.config.translation)
                refs.append({"reference": v["reference"], "usfm": v["usfm"],
                             "translation": fetched["translation"], "text": fetched["text"]})
                self.engine.memory.add("guide:" + self._user, beat.themes, beat.intensity,
                                       v["reference"])
        return refs

    def reply(self, text, user_id: str = "guide", history=None, voice: bool = False) -> dict:
        """history: [{"role": "user"|"assistant", "content": str}, ...] most recent last."""
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "text required"}
        self._user = user_id

        # safety gate first — a crisis ends the conversation turn with help, not chat
        if self.engine.gloo.safety_text(text):
            return {"ok": True, "safety": True, "reply": SAFETY_MESSAGE, "refs": [],
                    "guardian": self.engine.guardian.alert(user_id)}

        refs = self._ground(text)
        context = "\n".join('%s (%s): "%s"' % (r["reference"], r["translation"], r["text"])
                            for r in refs) or "(empty)"
        system = PERSONA + "\n\nCONTEXT:\n" + context
        if voice:
            system += ("\n\nThis is a VOICE call: answer in at most 3 short spoken "
                       "sentences, no lists, no markdown.")
        msgs = [{"role": m.get("role", "user"), "content": str(m.get("content", ""))[:1500]}
                for m in (history or [])[-8:] if m.get("content")]
        msgs.append({"role": "user", "content": text})

        answer = self.engine.gloo.converse(system, msgs)
        return {"ok": True, "safety": False, "reply": answer.strip(), "refs": refs}
