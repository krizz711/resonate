"""Tiny stdlib .env loader (no python-dotenv dependency).

Called by ENTRYPOINTS only (scripts/serve.py, scripts/live_check.py, scripts/demo.py) —
never by the library or tests, so the test/eval suites stay deterministic-mock even when
a .env with live keys sits in the repo. Existing environment variables always win.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env(path=None) -> int:
    """Load KEY=VALUE lines from .env (comments/blanks ignored, quotes stripped).
    Returns the number of variables applied. Never overrides existing env."""
    p = Path(path) if path else ROOT / ".env"
    if not p.is_file():
        return 0
    applied = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.split(" #")[0].strip().strip('"').strip("'")
        if key and key not in os.environ and val != "":
            os.environ[key] = val
            applied += 1
    return applied
