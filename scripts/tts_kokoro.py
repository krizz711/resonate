"""Kokoro synthesis worker — runs INSIDE the Kokoro venv, not the project venv.

serve.py shells out to this with the venv's python (heavy TTS deps live only there):
  <kokoro-venv>/Scripts/python.exe scripts/tts_kokoro.py --voice bf_isabella \
      --speed 0.86 --out C:/short/path.wav "The Lord is close to the brokenhearted."

Writes a mono 24 kHz WAV. Keep --out on a SHORT path (Kokoro/soundfile fails on very
long Windows paths). Prints DONE <seconds-of-audio> on success.
"""
import argparse
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="af_bella")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("text")
    a = ap.parse_args()
    secs = synth(a.text, a.voice, a.speed, a.out)
    print("DONE %.2f" % secs)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("FAIL %s" % e, file=sys.stderr)
        sys.exit(1)
