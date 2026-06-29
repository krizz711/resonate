"""Provider factories — pick mock (offline) or live (real APIs) by config.provider_mode."""
from .gloo import MockGloo, LiveGloo
from .youversion import MockYouVersion, LiveYouVersion


def make_gloo(config):
    return LiveGloo(config) if config.provider_mode == "live" else MockGloo(config)


def make_youversion(config):
    return LiveYouVersion(config) if config.provider_mode == "live" else MockYouVersion(config)
