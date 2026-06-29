from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Beat:
    """One emotional/thematic unit extracted from the input text (stage 1)."""
    index: int
    text: str
    themes: list
    emotion: str
    intensity: float
    timestamp: str | None = None
