from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# config.py lives at <project>/resonate/config.py -> parents[1] is the project root.
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


@dataclass
class Weights:
    """Tunable weights for the post-fusion fit score (see ENGINE-DESIGN.md, stage 4)."""
    rrf: float = 1.0     # base hybrid relevance (normalized RRF)
    tone: float = 0.8    # tone/posture fit for the beat's intensity
    recent: float = 0.9  # PENALTY: verse used recently
    repeat: float = 0.5  # PENALTY: same theme hammered recently
    arc: float = 0.4     # narrative continuity with the person's recurring themes


@dataclass
class EngineConfig:
    # "mock" runs fully offline (local embeddings + sample texts + local memory) so we can
    # build now, before competition keys exist. "live" flips to the real Gloo + YouVersion APIs.
    provider_mode: str = field(default_factory=lambda: os.getenv("RESONATE_MODE", "mock"))
    translation: str = field(default_factory=lambda: os.getenv("RESONATE_TRANSLATION", "KJV"))

    topk: int = 12              # candidates kept after retrieval/fusion
    rrf_k: int = 60             # RRF constant
    recency_window: int = 8     # last N delivered verses count as "recent"
    abstain_margin: float = 0.08  # if top two are within this, flag low confidence

    weights: Weights = field(default_factory=Weights)

    # memory/storage backend: "local" (default) or "redis"; redis auto-falls-back to local.
    memory_backend: str = field(default_factory=lambda: os.getenv("RESONATE_MEMORY", "local"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))

    # --- live API config (only used when provider_mode == "live") -------------
    # NOTE: base URLs / model id are placeholders to confirm during integration (keys open 2026-07-06).
    gloo_api_key: str = field(default_factory=lambda: os.getenv("GLOO_API_KEY", ""))
    gloo_base_url: str = field(default_factory=lambda: os.getenv("GLOO_BASE_URL", "https://platform.ai.gloo.com/ai/v1"))
    gloo_model: str = field(default_factory=lambda: os.getenv("GLOO_MODEL", ""))  # set to a Gloo-hosted model id at integration
    yv_app_key: str = field(default_factory=lambda: os.getenv("YOUVERSION_APP_KEY", ""))
    yv_base_url: str = field(default_factory=lambda: os.getenv("YOUVERSION_BASE_URL", "https://api.youversion.com/v1"))
    bible_id: str = field(default_factory=lambda: os.getenv("RESONATE_BIBLE_ID", ""))
