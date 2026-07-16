from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# config.py lives at <project>/resonate/config.py -> parents[1] is the project root.
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


@dataclass
class Weights:
    """Tunable weights for the post-fusion fit score (see ENGINE-DESIGN.md, stage 4).
    Tuned against eval/run_eval.py."""
    rrf: float = 1.0     # base hybrid relevance (normalized RRF)
    theme: float = 0.7   # explicit theme-cover bonus (high-precision)
    tone: float = 0.5    # tone/posture fit for the beat's intensity
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
    history_max: int = 3        # prior user messages blended into retrieval context

    weights: Weights = field(default_factory=Weights)

    # memory/storage backend: "local" (default) or "redis"; redis auto-falls-back to local.
    memory_backend: str = field(default_factory=lambda: os.getenv("RESONATE_MEMORY", "local"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))
    # persist memory to disk so recurring themes accumulate across sessions ("returned N times").
    # OFF by default so tests/eval/demo stay deterministic; the server turns it on.
    memory_persist: bool = field(default_factory=lambda: os.getenv("RESONATE_PERSIST", "0") == "1")
    memory_path: str = field(default_factory=lambda: os.getenv("RESONATE_MEMORY_PATH", str(DATA_DIR / ".memory.json")))

    # --- live API config (only used when provider_mode == "live") -------------
    # Verified against docs.gloo.com + developers.youversion.com on 2026-07-04.
    # Gloo: OAuth2 client-credentials (Studio Dashboard -> API Credentials).
    gloo_client_id: str = field(default_factory=lambda: os.getenv("GLOO_CLIENT_ID", ""))
    gloo_client_secret: str = field(default_factory=lambda: os.getenv("GLOO_CLIENT_SECRET", ""))
    gloo_base_url: str = field(default_factory=lambda: os.getenv("GLOO_BASE_URL", "https://platform.ai.gloo.com"))
    gloo_model: str = field(default_factory=lambda: os.getenv("GLOO_MODEL", ""))  # empty => auto_routing=true
    gloo_tradition: str = field(default_factory=lambda: os.getenv("GLOO_TRADITION", ""))  # optional theological lens
    # Pinned model for structured tasks (segment/verify/bridge). auto_routing's values-aligned
    # router sends emotional text to pastoral chat models that answer with care instead of JSON
    # (observed live 2026-07-10); stories keep auto_routing, where that warmth is the point.
    gloo_model_structured: str = field(default_factory=lambda: os.getenv("GLOO_MODEL_STRUCTURED", "gloo-anthropic-claude-haiku-4.5"))
    # Scripture Guide conversations: haiku keeps a voice call snappy; set empty to let
    # auto_routing pick (pastoral warmth, unknown latency/cost per turn).
    gloo_model_guide: str = field(default_factory=lambda: os.getenv("GLOO_MODEL_GUIDE", "gloo-anthropic-claude-haiku-4.5"))
    # YouVersion: app key from platform.youversion.com (accept each Bible's license there first).
    yv_app_key: str = field(default_factory=lambda: os.getenv("YOUVERSION_APP_KEY", ""))
    yv_base_url: str = field(default_factory=lambda: os.getenv("YOUVERSION_BASE_URL", "https://api.youversion.com/v1"))
    bible_id: str = field(default_factory=lambda: os.getenv("RESONATE_BIBLE_ID", ""))  # numeric id; resolve via scripts/live_check.py
    # persist fetched YouVersion text to disk (data/.yv-cache.json) so verses are fetched
    # at most once ever. OFF by default (tests stay hermetic); the server turns it on.
    yv_cache_persist: bool = field(default_factory=lambda: os.getenv("RESONATE_YV_CACHE", "0") == "1")

    # unknown-theme tally (sanitized labels + counts ONLY, never the person's words) —
    # the corpus's growth signal: /health surfaces what people felt that the vocabulary
    # couldn't answer. OFF by default (tests stay hermetic); the server turns it on.
    gaps_persist: bool = field(default_factory=lambda: os.getenv("RESONATE_GAPS", "0") == "1")
    gaps_path: str = field(default_factory=lambda: os.getenv("RESONATE_GAPS_PATH", str(DATA_DIR / ".theme-gaps.json")))

    # --- guardian alerts (security module; consent-first, see resonate/guardian.py) ---
    guardian_enabled: bool = field(default_factory=lambda: os.getenv("RESONATE_GUARDIAN", "0") == "1")
    guardian_file: str = field(default_factory=lambda: os.getenv("GUARDIAN_FILE", str(DATA_DIR / "guardians.json")))
    guardian_cooldown_h: float = field(default_factory=lambda: float(os.getenv("GUARDIAN_COOLDOWN_H", "24")))
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_from: str = field(default_factory=lambda: os.getenv("SMTP_FROM", ""))
    twilio_sid: str = field(default_factory=lambda: os.getenv("TWILIO_SID", ""))
    twilio_token: str = field(default_factory=lambda: os.getenv("TWILIO_TOKEN", ""))
    twilio_whatsapp_from: str = field(default_factory=lambda: os.getenv("TWILIO_WHATSAPP_FROM", ""))
