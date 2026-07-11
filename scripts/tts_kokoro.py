"""Kokoro synthesis worker — runs INSIDE the Kokoro venv, not the project venv.

One-shot (original) mode — serve.py shells out per render:
  <kokoro-venv>/Scripts/python.exe scripts/tts_kokoro.py --voice bf_isabella \
      --speed 0.86 --out C:/short/path.wav "The Lord is close to the brokenhearted."
  Writes a mono 24 kHz WAV; prints DONE <seconds-of-audio>.

Persistent mode (--serve) — the model loads ONCE, then a JSON-line loop turns
each request around in synthesis time only (a live call needs this; a fresh
process pays ~8s of model load per reply):
  stdin :  {"voice": "af_bella", "speed": 0.88, "text": "...", "out": "C:/ktts/x.wav"}
           {"op": "ping"}                      (warmup / liveness)
  stdout:  {"ok": true, "secs": 3.1}           (one line per request)
           {"ok": false, "error": "..."}

Keep --out/"out" on a SHORT path (Kokoro/soundfile fails on very long Windows paths).
"""
import argparse
import json
import sys

LANG_FOR_VOICE = {"af_": "a", "am_": "a", "bf_": "b", "bm_": "b"}

_PIPES = {}


def pipeline_for(voice):
    from kokoro import KPipeline
    lang = LANG_FOR_VOICE.get(voice[:3], "a")
    if lang not in _PIPES:
        _PIPES[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
    return _PIPES[lang]


def synth(text, voice, speed, out_path):
    import numpy as np
    import soundfile as sf
    pipe = pipeline_for(voice)
    chunks = [np.asarray(audio) for _, _, audio in pipe(text, voice=voice, speed=speed)]
    if not chunks:
        raise RuntimeError("kokoro produced no audio")
    wav = np.concatenate(chunks)
    sf.write(out_path, wav, 24000)
    return len(wav) / 24000.0


def serve():
    """Persistent JSON-line loop. stdout is protocol-only; logs go to stderr."""
    print("kokoro-worker: ready", file=sys.stderr, flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            if req.get("op") == "ping":
                # a warm ping loads the model so the first real reply is fast
                pipeline_for(req.get("warm_voice", "af_bella"))
                resp = {"ok": True, "pong": True}
            else:
                secs = synth(req["text"], req.get("voice", "af_bella"),
                             float(req.get("speed", 1.0)), req["out"])
                resp = {"ok": True, "secs": round(secs, 2)}
        except Exception as e:
            resp = {"ok": False, "error": str(e)[:300]}
        print(json.dumps(resp), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true", help="persistent stdin/stdout worker")
    ap.add_argument("--voice", default="af_bella")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--out")
    ap.add_argument("text", nargs="?")
    a = ap.parse_args()
    if a.serve:
        serve()
        return
    if not a.out or a.text is None:
        ap.error("--out and text are required in one-shot mode")
    secs = synth(a.text, a.voice, a.speed, a.out)
    print("DONE %.2f" % secs)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("FAIL %s" % e, file=sys.stderr)
        sys.exit(1)
