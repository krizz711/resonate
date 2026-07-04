"""Voice lab — render a tuning matrix of the three chosen Kokoro voices so the
'godly' presets can be judged by ear, not by guess.

For each voice (bella / isabella / george) it renders the shipped preset plus
speed and pitch variations, writes WAVs to data/voice-lab/, and generates an
index.html audition page (open it directly, or via the engine server at
/voice-lab.html after copying — simplest: open the file in a browser).

Run (system python; synthesis is delegated to the Kokoro venv automatically):
  python scripts/voice_lab.py            # default verse line
  python scripts/voice_lab.py "text..."  # custom line
"""
import os
import sys
import time
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resonate import tts  # noqa: E402
from resonate.config import DATA_DIR  # noqa: E402

OUT = DATA_DIR / "voice-lab"

DEFAULT_TEXT = ("Come unto me, all ye that labour and are heavy laden, "
                "and I will give you rest.")

# Variations around each shipped preset: (tag, speed delta, pitch delta)
VARIANTS = [
    ("preset", 0.00, 0.0),
    ("slower", -0.06, 0.0),
    ("faster", +0.06, 0.0),
    ("deeper", 0.00, -1.5),
    ("deepest", 0.00, -3.0),
    ("plain", 0.00, 0.0),  # no reverb/bass — the 'phone assistant' control
]


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TEXT
    if not tts.available():
        print("Kokoro venv or ffmpeg unavailable — voice lab needs both. "
              "(RESONATE_KOKORO_PY=%s)" % tts.KOKORO_PY)
        sys.exit(1)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for vid, preset in tts.PRESETS.items():
        for tag, dspeed, dpitch in VARIANTS:
            p = replace(preset,
                        speed=round(preset.speed + dspeed, 3),
                        pitch_semitones=preset.pitch_semitones + dpitch)
            if tag == "plain":
                p = replace(preset, pitch_semitones=0.0, bass_gain_db=0.0,
                            reverb="anull", speed=1.0)
            name = "%s_%s.wav" % (vid, tag)
            path = OUT / name
            t0 = time.time()
            try:
                tts.generate_to(p, text, path)
                print("%-24s %5.1fs  (speed %.2f, pitch %+.1f st)" %
                      (name, time.time() - t0, p.speed, p.pitch_semitones))
                rows.append((vid, tag, name, p))
            except Exception as e:
                print("%-24s FAILED: %s" % (name, e))

    html = ["<!doctype html><meta charset='utf-8'><title>Resonate voice lab</title>",
            "<body style='font-family:Georgia,serif;background:#efe9df;color:#211d17;padding:32px;max-width:860px;margin:auto'>",
            "<h1 style='letter-spacing:.06em'>Voice lab — pick the godly one</h1>",
            "<p style='color:#6b6358'>Text: <i>%s</i></p>" % text]
    for vid in tts.PRESETS:
        html.append("<h2 style='color:#a65b43;margin-top:28px'>%s</h2>" % tts.PRESETS[vid].label)
        for r_vid, tag, name, p in rows:
            if r_vid != vid:
                continue
            html.append(
                "<div style='margin:10px 0'><b style='display:inline-block;width:90px'>%s</b> "
                "<audio controls preload='none' src='%s'></audio> "
                "<small style='color:#6b6358'>speed %.2f · pitch %+.1f st · bass %+.1f dB</small></div>"
                % (tag, name, p.speed, p.pitch_semitones, p.bass_gain_db))
    html.append("<p style='margin-top:30px;color:#6b6358'>Adjust the winners into "
                "<code>resonate/tts.py PRESETS</code>, then delete <code>data/.tts-cache</code>.</p></body>")
    (OUT / "index.html").write_text("\n".join(html), encoding="utf-8")
    print("\nAudition page: %s" % (OUT / "index.html"))


if __name__ == "__main__":
    main()
