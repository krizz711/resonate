"""Delivery layer — the "choose your destination" architecture.

The engine emits a neutral `delivery` dict. A DeliveryTarget adapts it for one surface
(VS Code margin, Discord message, wearable line, console). Adding a new surface = adding a new
target, with zero engine changes — this is what makes "you decide where the verse appears" true.
"""
from __future__ import annotations


def _shorten(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


class DeliveryTarget:
    name = "base"

    def adapt(self, d: dict) -> dict:
        raise NotImplementedError


class VSCodeTarget(DeliveryTarget):
    """Scripture in the editor margins: a status-bar label + a rich hover."""
    name = "vscode"

    def adapt(self, d):
        ref = d["reference"]
        tooltip = "**%s** (%s)\n\n%s\n\n_%s_" % (ref, d["translation"], d["verse_text"], d["bridge"])
        return {"statusText": "✝ %s" % ref, "tooltipMarkdown": tooltip,
                "reference": ref, "translation": d["translation"],
                "verseText": d["verse_text"], "bridge": d["bridge"], "themes": d["beat"]["themes"]}


class DiscordTarget(DeliveryTarget):
    """Scripture as conversation, not broadcast."""
    name = "discord"

    def adapt(self, d):
        return {"content": "%s\n> %s\n— *%s* (%s)" % (d["bridge"], d["verse_text"], d["reference"], d["translation"])}


class WearableTarget(DeliveryTarget):
    """The right word at the right moment — one glanceable line."""
    name = "wearable"

    def adapt(self, d):
        return {"title": d["reference"], "line": _shorten(d["verse_text"], 90)}


class ConsoleTarget(DeliveryTarget):
    name = "console"

    def adapt(self, d):
        return {"text": "%s\n%s — %s (%s)" % (d["bridge"], d["verse_text"], d["reference"], d["translation"])}


TARGETS = {t.name: t for t in [VSCodeTarget(), DiscordTarget(), WearableTarget(), ConsoleTarget()]}


def render(result: dict, target_names) -> dict:
    """Adapt every delivered verse in a result for each requested target."""
    out = {}
    for name in target_names:
        target = TARGETS.get(name)
        if not target:
            continue
        out[name] = [target.adapt(d) for d in result["deliveries"] if d.get("status") == "delivered"]
    return out
