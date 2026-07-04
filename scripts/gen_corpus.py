"""Training-corpus generator for the emotion->Scripture matcher (the ML centerpiece).

Produces data/corpus/train.jsonl — one line per (message -> gold verse) pair with
theme labels and mined hard negatives — for fine-tuning a small bi-encoder retriever
("the first open emotion->Scripture retrieval model", trained + ablated in the public
Kaggle notebook).

Two generators behind one format:
  --mock (default)  template-based smoke data. Runs today, proves the pipeline &
                    trainer end-to-end. NOT for the final model: templates draw on the
                    same lexicon the baseline uses, so a model trained on them just
                    re-learns the lexicon (circular).
  --live            Gloo AI as the data teacher (needs keys, 2026-07-06): diverse,
                    natural first-person messages a person might really type — the
                    corpus the shipped model trains on. Resumable; --max-calls guard.

Run:  python scripts/gen_corpus.py --mock --per-verse 8
      python scripts/gen_corpus.py --live --per-verse 12 --max-calls 200
"""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resonate.envfile import load_env  # noqa: E402

load_env()

from resonate.config import DATA_DIR, EngineConfig  # noqa: E402

OUT_DIR = DATA_DIR / "corpus"

# --- mock templates: situation x feeling, per theme ---------------------------
SITUATIONS = [
    "with my exams", "at work", "with my startup", "with my family", "about money",
    "in my marriage", "with this project", "late at night", "with my health",
    "after moving to a new city", "with everything lately", "since the diagnosis",
    "after the breakup", "raising my kids", "with the deadline tomorrow",
]
FEELING = {
    "anxiety": ["I can't stop worrying", "my chest is tight with worry", "I'm spiraling about everything"],
    "fear": ["I'm honestly scared", "I'm terrified of what comes next", "the fear won't let go"],
    "grief": ["I lost someone and it still hurts", "the grief comes in waves", "I'm mourning and nobody sees it"],
    "loneliness": ["I feel completely alone", "nobody would notice if I vanished for a bit", "I'm so isolated"],
    "doubt": ["I'm questioning everything", "I'm not sure any of this matters", "my faith feels thin"],
    "guilt": ["I keep replaying what I did", "I feel like it's all my fault", "the shame won't lift"],
    "anger": ["I'm so angry I can't think", "the resentment is eating me", "I'm furious and stuck"],
    "weariness": ["I'm completely exhausted", "I'm running on empty", "I can't keep going like this"],
    "gratitude": ["I'm unexpectedly thankful today", "something good happened and I'm grateful", "I feel blessed"],
    "joy": ["I'm genuinely happy for once", "I can't stop smiling today", "something wonderful happened"],
    "hope": ["I'm daring to hope again", "maybe better days are coming", "I want to believe it gets better"],
    "peace": ["I just want some calm", "I can't find any peace", "my mind won't go quiet"],
    "perseverance": ["I want to give up but haven't", "I'm barely pushing through", "I keep hitting the same wall"],
    "purpose": ["I don't know why I'm doing any of this", "I feel directionless", "what am I even for"],
    "provision": ["I can't cover the bills", "money is impossibly tight", "I don't know how we'll afford it"],
    "forgiveness": ["I can't forgive them", "I need to be forgiven", "I keep carrying what they did"],
    "love": ["I feel unloved", "I'm longing for someone to stay", "I don't feel chosen by anyone"],
    "comfort": ["everything hurts right now", "I'm aching and tired of pretending", "I just need comfort"],
    "courage": ["I don't feel brave enough for this", "I keep shrinking back", "I need courage I don't have"],
    "rest": ["I can't sleep", "I don't remember my last real break", "I'm restless every night"],
    "identity": ["I don't feel like I'm enough", "I keep failing at being me", "I don't know who I am anymore"],
    "trust": ["I can't let go of control", "trusting feels impossible", "I'm white-knuckling everything"],
    "prayer": ["I don't have words to pray", "I keep praying into silence", "all I can do is pray"],
}


def load_verses():
    data = json.loads((DATA_DIR / "verses.json").read_text(encoding="utf-8"))
    return data["verses"]


def mine_hard_negatives(verse, verses, rng, k=4):
    """Near-misses: share >=1 theme with the gold verse but are NOT it — the pairs a
    lexical matcher confuses and a trained encoder must separate."""
    gold_themes = set(verse.get("themes", []))
    near = [v["usfm"] for v in verses
            if v["usfm"] != verse["usfm"] and gold_themes & set(v.get("themes", []))]
    far = [v["usfm"] for v in verses
           if v["usfm"] != verse["usfm"] and not (gold_themes & set(v.get("themes", [])))]
    rng.shuffle(near)
    rng.shuffle(far)
    return near[:k] + far[:2]


def gen_mock(verses, per_verse, rng):
    rows = []
    for v in verses:
        themes = v.get("themes", [])
        if not themes:
            continue
        for i in range(per_verse):
            theme = themes[i % len(themes)]
            feel = rng.choice(FEELING.get(theme, ["I feel %s" % theme]))
            sit = rng.choice(SITUATIONS)
            intensity = rng.choice(["", " so much", " honestly", " completely", ""])
            text = "%s %s%s." % (feel, sit, intensity)
            rows.append({"text": text.strip(), "gold_usfm": v["usfm"],
                         "gold_reference": v["reference"], "themes": themes,
                         "tone": v.get("tone", ""), "source": "mock",
                         "hard_negatives": mine_hard_negatives(v, verses, rng)})
    return rows


def gen_live(verses, per_verse, max_calls, rng):
    from resonate.providers.gloo import LiveGloo
    gloo = LiveGloo(EngineConfig())
    rows, calls = [], 0
    sys_p = ("You generate realistic first-person messages people type to an AI assistant "
             "in honest moments. Given a verse's themes and pastoral note, write %d diverse, "
             "natural messages (1-2 sentences each, varied situations: study, work, money, "
             "family, health, night-time) for which that verse would TRULY fit. Do NOT use "
             "the verse's own words or any Bible vocabulary. Return ONLY a JSON array of "
             "strings." % per_verse)
    for v in verses:
        if calls >= max_calls:
            print("  max-calls reached, stopping (resumable).")
            break
        prompt = "Themes: %s\nTone: %s\nPastoral note: %s" % (
            ", ".join(v.get("themes", [])), v.get("tone", ""), v.get("note", ""))
        try:
            raw = gloo._chat(sys_p, prompt, temperature=0.9)
            calls += 1
            texts = json.loads(raw[raw.find("["):raw.rfind("]") + 1])
        except Exception as e:
            print("  skip %s: %s" % (v["reference"], str(e)[:80]))
            continue
        for t in texts[:per_verse]:
            if isinstance(t, str) and t.strip():
                rows.append({"text": t.strip(), "gold_usfm": v["usfm"],
                             "gold_reference": v["reference"], "themes": v.get("themes", []),
                             "tone": v.get("tone", ""), "source": "gloo",
                             "hard_negatives": mine_hard_negatives(v, verses, rng)})
        print("  %s -> %d messages (%d calls)" % (v["reference"], len(texts), calls))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--per-verse", type=int, default=8)
    ap.add_argument("--max-calls", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    verses = load_verses()
    print("verses: %d | mode: %s" % (len(verses), "live" if a.live else "mock"))
    rows = gen_live(verses, a.per_verse, a.max_calls, rng) if a.live \
        else gen_mock(verses, a.per_verse, rng)
    rng.shuffle(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / ("train_live.jsonl" if a.live else "train_mock.jsonl")
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    themes = {}
    for r in rows:
        for t in r["themes"]:
            themes[t] = themes.get(t, 0) + 1
    print("wrote %d pairs -> %s" % (len(rows), out))
    print("theme coverage: %s" % ", ".join("%s:%d" % kv for kv in sorted(themes.items())))


if __name__ == "__main__":
    main()
