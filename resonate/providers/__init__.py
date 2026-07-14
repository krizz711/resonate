"""Provider factories — pick mock (offline) or live (real APIs) by config.provider_mode.

Modes:
  "mock" — fully offline (tests/eval/demo default).
  "live" — force the real APIs (scripts/live_check.py preflight).
  "auto" — the hosted default: each provider goes live exactly when its own
           credentials exist (Gloo: client id+secret; YouVersion: app key+bible id)
           and stays mock otherwise. A keyless deploy is byte-identical to mock,
           so adding keys in the dashboard is the ONLY step to go live — and a
           missing key can never half-break the site.
"""
from .gloo import MockGloo, LiveGloo
from .youversion import MockYouVersion, LiveYouVersion


def make_gloo(config):
    live = config.provider_mode == "live" or (
        config.provider_mode == "auto"
        and config.gloo_client_id and config.gloo_client_secret)
    return LiveGloo(config) if live else MockGloo(config)


def make_youversion(config):
    live = config.provider_mode == "live" or (
        config.provider_mode == "auto"
        and config.yv_app_key and config.bible_id)
    return LiveYouVersion(config) if live else MockYouVersion(config)
