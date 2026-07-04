"""Voice of Resonate — Kokoro TTS with 'godly' post-processing presets.

Three voices the user chose from Kokoro, each with a tuned preset (speed into Kokoro;
pitch/bass/reverb via an ffmpeg chain) so the verse sounds unhurried and reverent —
a voice from an old chapel, not a phone assistant:

  bella    (af_bella)    warm American female — gentle, close
  isabella (bf_isabella) British female       — luminous, formal
  george   (bm_george)   British male         — deep, patriarchal

Synthesis runs in the separate Kokoro venv via scripts/tts_kokoro.py (subprocess), the
result is post-processed with ffmpeg and cached on disk by (voice, preset, text) hash.
If the venv or ffmpeg is missing, available() is False and callers fall back to the
browser's Web Speech — the demo never breaks.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from .config import DATA_DIR, ROOT

KOKORO_PY = os.getenv(
    "RESONATE_KOKORO_PY",
    r"C:\dev\mcp-servers\kokoro-mcp-server\.venv\Scripts\python.exe",
)
WORKER = str(ROOT / "scripts" / "tts_kokoro.py")
CACHE_DIR = Path(os.getenv("RESONATE_TTS_CACHE", str(DATA_DIR / ".tts-cache")))
# Kokoro/soundfile chokes on very long Windows paths -> raw synth goes to a short temp dir.
SHORT_TMP = Path(os.getenv("RESONATE_TTS_TMP", r"C:\ktts"))


@dataclass
class VoicePreset:
    kokoro_voice: str
    label: str
    speed: float          # Kokoro-native tempo (1.0 = normal)
    pitch_semitones: float  # negative = deeper (ffmpeg asetrate/atempo trick)
    bass_gain_db: float   # low-shelf warmth
    bass_freq: int
    reverb: str           # ffmpeg aecho args — the quiet-chapel tail
    loudness_i: float = -17.0  # loudnorm integrated target (LUFS); higher = louder


# The "godly" defaults. scripts/voice_lab.py renders a whole tuning matrix so the
# user can audition and adjust these by ear.
# User picks (2026-07-04): Bella = the shipped preset (favorite). George = his
# ORIGINAL Kokoro voice (no pitch drop, minimal colour) but noticeably LOUDER.
PRESETS = {
    "bella": VoicePreset("af_bella", "Bella — warm, close", 0.88, -1.0, 3.0, 110,
                         "aecho=0.72:0.68:52|84:0.20|0.14"),
    "isabella": VoicePreset("bf_isabella", "Isabella — luminous, formal", 0.86, -1.5, 2.5, 120,
                            "aecho=0.74:0.70:58|92:0.22|0.15"),
    "george": VoicePreset("bm_george", "George — natural, fuller", 0.94, 0.0, 1.5, 100,
                          "aecho=0.68:0.64:46|74:0.14|0.10", loudness_i=-12.0),
}

_GEN_LOCK = threading.Lock()  # one synthesis at a time — Kokoro is heavy on this laptop


def available() -> bool:
    return os.path.isfile(KOKORO_PY) and shutil.which("ffmpeg") is not None


def voices() -> list:
    return [{"id": k, "label": p.label, "kokoro": p.kokoro_voice} for k, p in PRESETS.items()]


def _pitch_chain(semitones: float) -> str:
    """Pitch shift preserving duration: resample-rate trick + inverse atempo."""
    if abs(semitones) < 0.05:
        return ""
    f = 2.0 ** (semitones / 12.0)
    return "asetrate=24000*%.6f,aresample=24000,atempo=%.6f" % (f, 1.0 / f)


def _fx_chain(p: VoicePreset) -> str:
    parts = [c for c in (
        _pitch_chain(p.pitch_semitones),
        ("bass=g=%.1f:f=%d" % (p.bass_gain_db, p.bass_freq)) if abs(p.bass_gain_db) > 0.05 else "",
        p.reverb,
        "loudnorm=I=%.0f:TP=-1.5:LRA=9" % p.loudness_i,
    ) if c]
    return ",".join(parts)


def cache_key(voice_id: str, text: str, preset: VoicePreset) -> str:
    h = hashlib.sha1()
    h.update(("%s|%.3f|%.2f|%.1f|%.1f|%s|%s" % (
        preset.kokoro_voice, preset.speed, preset.pitch_semitones,
        preset.bass_gain_db, preset.loudness_i, preset.reverb, text.strip())).encode("utf-8"))
    return "%s_%s" % (voice_id, h.hexdigest()[:20])


def synthesize(voice_id: str, text: str) -> Path:
    """Return a cached-or-generated WAV path. Raises on failure (callers turn that
    into a Web Speech fallback)."""
    preset = PRESETS.get(voice_id)
    if preset is None:
        raise ValueError("unknown voice %r (have: %s)" % (voice_id, ", ".join(PRESETS)))
    text = (text or "").strip()
    if not text:
        raise ValueError("empty text")
    if len(text) > 800:
        text = text[:800]

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = CACHE_DIR / (cache_key(voice_id, text, preset) + ".wav")
    if out.is_file() and out.stat().st_size > 44:
        return out

    if not available():
        raise RuntimeError("kokoro venv or ffmpeg not available")

    with _GEN_LOCK:
        if out.is_file() and out.stat().st_size > 44:  # lost the race -> already done
            return out
        generate_to(preset, text, out)
    return out


def generate_to(preset: VoicePreset, text: str, out) -> None:
    """Raw synthesis: Kokoro (in its venv) -> ffmpeg preset chain -> out path.
    No cache, no lock — synthesize() wraps this; scripts/voice_lab.py calls it
    directly with experimental presets."""
    SHORT_TMP.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(suffix=".wav", dir=str(SHORT_TMP))
    os.close(fd)
    try:
        r = subprocess.run(
            [KOKORO_PY, WORKER, "--voice", preset.kokoro_voice,
             "--speed", str(preset.speed), "--out", raw, text],
            capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise RuntimeError("kokoro synth failed: %s" % (r.stderr or r.stdout).strip()[:300])
        f = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-i", raw, "-filter:a", _fx_chain(preset), "-ar", "24000", "-ac", "1", str(out)],
            capture_output=True, text=True, timeout=120)
        if f.returncode != 0:
            raise RuntimeError("ffmpeg fx failed: %s" % f.stderr.strip()[:300])
    finally:
        try:
            os.unlink(raw)
        except OSError:
            pass
