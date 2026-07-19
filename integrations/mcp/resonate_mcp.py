"""Resonate MCP server — Scripture as a native capability for ANY AI assistant.

Pure standard library (like the rest of the engine): JSON-RPC 2.0 over stdio,
speaking the Model Context Protocol. Point Claude Desktop / Claude Code /
ChatGPT developer mode at this file and the assistant itself can:

  resonate_verse    hear a moment -> a verified verse (or restrained silence)
  generate_story    weave the user's moment into a vetted biblical narrative
  reel_groups       prioritized "reels for you" sets for the moment's themes
  fetch_passage     verbatim licensed passage text (YouVersion in live mode)

The engine's guarantees hold server-side no matter what the model asks for:
the safety gate always runs first (crisis -> help resources, never a verse),
verse text comes only from the provider (never model memory), stories carry
the "not Scripture" label, and per-user series memory spans every surface —
the same engine that powers the browser extension answers here.

Design note on restraint: the Delivery Policy throttles UNSOLICITED surfacing
(the extension). An explicit tool call is consent, so solicited calls always
answer — but safety still overrides consent.

Run:  python integrations/mcp/resonate_mcp.py     (stdout = protocol, logs -> stderr)
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from resonate.envfile import load_env  # noqa: E402

load_env()

from resonate import Engine, EngineConfig  # noqa: E402
from resonate.reels import ReelStore  # noqa: E402
from resonate.story import StoryWeaver  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "resonate", "version": "0.4.0"}

_cfg = EngineConfig()
_cfg.memory_persist = True  # series memory spans assistants and sessions
ENGINE = Engine(_cfg)
WEAVER = StoryWeaver(ENGINE.gloo)
REELS = ReelStore()


def bind_engine(engine, weaver=None, reels=None):
    """Share ONE engine across surfaces. When serve.py hosts this module over HTTP it
    binds its OWN engine here, so the remote /mcp endpoint and the browser-extension
    /resonate write to the SAME per-user memory graph — one person, one context,
    whichever AI they connect from. Tool bodies read these module globals at call
    time, so reassigning them takes effect immediately."""
    global ENGINE, WEAVER, REELS
    ENGINE = engine
    if weaver is not None:
        WEAVER = weaver
    if reels is not None:
        REELS = reels

TOOLS = [
    {
        "name": "resonate_verse",
        "description": (
            "Given what a person just said (and optionally recent prior messages), return a "
            "verified Scripture verse that echoes their moment — with a one-line bridge and a "
            "confidence score — or an honest 'stay silent' when nothing truly resonates. "
            "If the text signals a crisis, returns crisis-help guidance instead of a verse "
            "(never quote a verse at a crisis). Verse text is fetched from a licensed source, "
            "never from model memory."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The person's message / moment."},
                "history": {"type": "array", "items": {"type": "string"},
                            "description": "Recent prior user messages, oldest first (optional)."},
                "user_id": {"type": "string", "description": "Stable id for series memory (optional)."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "generate_story",
        "description": (
            "Weave the person's present moment into ONE vetted biblical narrative — a short, "
            "warm second-person reflection ('your story') that ends on a verified verse quoted "
            "verbatim. The narrative comes from a curated shortlist; the reflection is clearly "
            "labeled 'not Scripture'. Refuses crisis input (returns help guidance instead)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The person's message / moment."},
                "history": {"type": "array", "items": {"type": "string"},
                            "description": "Recent prior user messages, oldest first (optional)."},
                "user_id": {"type": "string", "description": "Stable id for series memory (optional)."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "reel_groups",
        "description": (
            "Given what a person said (and optional prior messages), return small prioritized "
            "sets of story reels — 'reels for you' in watch order. Group 1: for the themes they "
            "just named; group 2: threads recurring in the conversation; group 3: steady "
            "comfort/hope anchors. Each group has a title, a one-line subtitle saying what it's "
            "for, and up to 3 reels (curated story films when available, licensed verse pages "
            "otherwise). Crisis input returns help guidance instead of reels."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The person's message / moment."},
                "history": {"type": "array", "items": {"type": "string"},
                            "description": "Recent prior user messages, oldest first (optional)."},
                "themes": {"type": "array", "items": {"type": "string"},
                           "description": "Explicit themes to group for (optional; overrides text segmentation)."},
            },
        },
    },
    {
        "name": "fetch_passage",
        "description": (
            "Fetch the verbatim licensed text of a Bible passage by USFM reference "
            "(e.g. JHN.3.16 or PHP.4.6-PHP.4.7). In live mode this is the YouVersion "
            "Platform API; the text should be quoted exactly, never paraphrased as Scripture."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "usfm": {"type": "string", "description": "USFM reference, e.g. JHN.3.16"},
                "translation": {"type": "string", "description": "Translation code (default KJV)."},
            },
            "required": ["usfm"],
        },
    },
]


# ---------------------------------------------------------------- tool bodies
def _tool_resonate_verse(args):
    text = (args.get("text") or "").strip()
    if not text:
        return {"kind": "error", "message": "text is required"}
    user = args.get("user_id") or "mcp_default"
    res = ENGINE.resonate(text, user, history=args.get("history") or [])
    held = next((d for d in res["deliveries"] if d["status"] == "safety_hold"), None)
    if held:
        return {"kind": "help", "message": held["message"],
                "note": "Crisis signals detected — share these resources; do not offer a verse."}
    delivered = [d for d in res["deliveries"] if d["status"] == "delivered"]
    if not delivered:
        return {"kind": "silent",
                "message": "No verse truly resonates with this — the honest answer is silence.",
                "context_themes": res.get("context", {}).get("themes", [])}
    d = delivered[0]
    return {"kind": "verse", "reference": d["reference"], "translation": d["translation"],
            "verse_text": d["verse_text"], "text_source": d["text_source"],
            "bridge": d["bridge"], "confidence": d["confidence"],
            "themes": d["beat"]["themes"], "memory_note": d.get("memory_note"),
            "quote_rule": "Quote verse_text exactly as given; it is licensed text."}


def _tool_generate_story(args):
    text = (args.get("text") or "").strip()
    if not text:
        return {"kind": "error", "message": "text is required"}
    user = args.get("user_id") or "mcp_default"
    res = ENGINE.resonate(text, user, history=args.get("history") or [])
    held = next((d for d in res["deliveries"] if d["status"] == "safety_hold"), None)
    if held:
        return {"kind": "help", "message": held["message"],
                "note": "Crisis signals detected — no story; share these resources."}
    delivered = [d for d in res["deliveries"] if d["status"] == "delivered"]
    if not delivered:
        return {"kind": "silent", "message": "No resonant moment to build a story from."}
    d = delivered[0]
    arcs = [t for t, _ in (ENGINE.memory.patterns(user).get("top_themes") or [])[:3]]
    narrative = WEAVER.select(d["beat"]["themes"],
                              res.get("context", {}).get("themes", []), arcs, user_id=user)
    if narrative is None:
        return {"kind": "silent", "message": "No fitting narrative for this moment."}
    verse = {"reference": d["reference"], "verse_text": d["verse_text"],
             "translation": d["translation"]}
    story = WEAVER.compose(text, d["beat"]["themes"], narrative, verse, user_id=user,
                           emotion=d["beat"].get("emotion", ""),
                           memory_note=d.get("memory_note"))
    return {"kind": "story", **story,
            "presentation_rule": "Present as a personal reflection; keep the label visible; "
                                 "the verse quote must remain verbatim."}


def _tool_reel_groups(args):
    text = (args.get("text") or "").strip()
    themes = [t for t in (args.get("themes") or []) if isinstance(t, str) and t.strip()]
    if not text and not themes:
        return {"kind": "error", "message": "text or themes is required"}
    if text and ENGINE.gloo.safety_text(text):
        return {"kind": "help", "message": "Crisis signals detected — share crisis resources; "
                                           "reels are not the right response here."}
    if not themes:
        beats = ENGINE.gloo.segment(text)
        themes = beats[0].themes if beats else []
    ctx = ENGINE._history_themes(args.get("history") or [])
    groups = REELS.groups_for(ENGINE.verses, themes, ctx, ENGINE.config.translation)
    if not groups:
        return {"kind": "silent", "message": "Nothing resonant enough to group reels for."}
    return {"kind": "reel_groups", "groups": groups,
            "presentation_rule": "Show groups in priority order with their subtitles; "
                                 "reel links open licensed pages or curated story films."}


def _tool_fetch_passage(args):
    usfm = (args.get("usfm") or "").strip()
    if not usfm:
        return {"kind": "error", "message": "usfm is required"}
    got = ENGINE.yv.fetch(usfm, args.get("translation"))
    return {"kind": "passage", **got,
            "quote_rule": "Quote text exactly as given; it is licensed text."}


_TOOL_FNS = {"resonate_verse": _tool_resonate_verse,
             "generate_story": _tool_generate_story,
             "reel_groups": _tool_reel_groups,
             "fetch_passage": _tool_fetch_passage}


# ---------------------------------------------------------------- JSON-RPC dispatch
def _result(rid, result):
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def dispatch(req, default_user=None):
    """Handle one JSON-RPC request dict -> response dict, or None for notifications.
    Pure function of the message (plus engine state) — unit-testable without stdio.

    default_user: the caller's Resonate Key (stdio --key, or the HTTP transport's
    ?key=). Injected as user_id into every tool call that didn't set one, so the
    same key means the same memory graph across AIs and devices. An explicit
    user_id in the arguments still wins."""
    method = req.get("method", "")
    rid = req.get("id")
    is_notification = "id" not in req

    if method == "initialize":
        return _result(rid, {"protocolVersion": PROTOCOL_VERSION,
                             "capabilities": {"tools": {}},
                             "serverInfo": SERVER_INFO})
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "ping":
        return _result(rid, {})
    if method == "tools/list":
        return _result(rid, {"tools": TOOLS})
    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name", "")
        fn = _TOOL_FNS.get(name)
        if fn is None:
            return _error(rid, -32602, "unknown tool: %s" % name)
        args = params.get("arguments") or {}
        if default_user and isinstance(args, dict) and not args.get("user_id"):
            args = dict(args, user_id=default_user)
        try:
            out = fn(args)
        except Exception as e:  # tool failure -> structured MCP error content
            return _result(rid, {"content": [{"type": "text", "text": json.dumps(
                {"kind": "error", "message": str(e)[:300]})}], "isError": True})
        return _result(rid, {"content": [{"type": "text",
                                          "text": json.dumps(out, ensure_ascii=False)}],
                             "isError": out.get("kind") == "error"})
    if is_notification:
        return None
    return _error(rid, -32601, "method not found: %s" % method)


def _key_from_argv():
    """A local stdio install can still share the one brain: pass --key RSN-XXXX
    (or set RESONATE_KEY) and this process tags its memory with that same key."""
    for i, a in enumerate(sys.argv):
        if a == "--key" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith("--key="):
            return a.split("=", 1)[1]
    return os.environ.get("RESONATE_KEY") or None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass
    key = _key_from_argv()
    sys.stderr.write("resonate-mcp: ready (mode=%s, key=%s)\n"
                     % (ENGINE.config.provider_mode, key or "none"))
    sys.stderr.flush()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps(_error(None, -32700, "parse error")) + "\n")
            sys.stdout.flush()
            continue
        resp = dispatch(req, default_user=key)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
