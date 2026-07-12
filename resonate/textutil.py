"""Plain-text hygiene for model output.

Everything Resonate renders is plain text (panel, call, wearable) and much of it is
SPOKEN — markdown must never survive, or Kokoro reads "asterisk asterisk" and the
bubble shows raw ** . Strip emphasis marks, code ticks, and leading header/bullet
markers; leave the words untouched.
"""
from __future__ import annotations

import re

_MD_LINE = re.compile(r"^\s{0,3}(#{1,6}\s+|[-*•]\s+)", re.M)
_MD_INLINE = re.compile(r"\*\*|\*|`|~~")


def plain_text(s: str, keep_newlines: bool = False) -> str:
    """Markdown -> prose. keep_newlines=True preserves paragraph breaks (stories);
    otherwise whitespace collapses to single spaces (chat/voice one-liners)."""
    s = _MD_LINE.sub("", s or "")
    s = _MD_INLINE.sub("", s)
    if keep_newlines:
        return re.sub(r"[ \t]+", " ", s).strip()
    return re.sub(r"\s+", " ", s).strip()
