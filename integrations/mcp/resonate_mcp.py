"""Resonate MCP server — Scripture as a native capability for ANY AI assistant.

Pure standard library (like the rest of the engine): JSON-RPC 2.0 over stdio,
speaking the Model Context Protocol. Point Claude Desktop / Claude Code /
ChatGPT developer mode at this file and the assistant itself can:

  resonate_verse    hear a moment -> a verified verse (or restrained silence)
  generate_story    weave the user's moment into a vetted biblical narrative
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
from resonate.story import StoryWeaver  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "resonate", "version": "0.3.0"}

_cfg = EngineConfig()
_cfg.memory_persist = True  # series memory spans assistants and sessions
ENGINE = Engine(_cfg)
WEAVER = StoryWeaver(ENGINE.gloo)

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


def _tool_fetch_passage(args):
    usfm = (args.get("usfm") or "").strip()
    if not usfm:
        return {"kind": "error", "message": "usfm is required"}
    got = ENGINE.yv.fetch(usfm, args.get("translation"))
    return {"kind": "passage", **got,
            "quote_rule": "Quote text exactly as given; it is licensed text."}


_TOOL_FNS = {"resonate_verse": _tool_resonate_verse,
             "generate_story": _tool_generate_story,
             "fetch_passage": _tool_fetch_passage}


# ---------------------------------------------------------------- JSON-RPC dispatch
def _result(rid, result):
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def dispatch(req):
    """Handle one JSON-RPC request dict -> response dict, or None for notifications.
    Pure function of the message (plus engine state) — unit-testable without stdio."""
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
        try:
            out = fn(params.get("arguments") or {})
        except Exception as e:  # tool failure -> structured MCP error content
            return _result(rid, {"content": [{"type": "text", "text": json.dumps(
                {"kind": "error", "message": str(e)[:300]})}], "isError": True})
        return _result(rid, {"content": [{"type": "text",
                                          "text": json.dumps(out, ensure_ascii=False)}],
                             "isError": out.get("kind") == "error"})
    if is_notification:
        return None
    return _error(rid, -32601, "method not found: %s" % method)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.stderr.write("resonate-mcp: ready (mode=%s)\n" % ENGINE.config.provider_mode)
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
        resp = dispatch(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
