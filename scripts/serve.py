"""Local Resonate engine server (Python standard library only).

A tiny JSON HTTP API the connectors (ChatGPT extension, VS Code, web panel, Discord) call.

Run:  python scripts/serve.py     ->  http://127.0.0.1:8765
Endpoints:
  GET  /health                      -> {ok, mode, targets, tts}
  GET  /voices                      -> {ok, available, voices:[{id,label}...]}
  GET  /tts?voice=bella&text=...    -> audio/wav (Kokoro + godly preset) | 503 {fallback}
  GET  /guide.html                  -> Ezra, the Scripture Guide — chat + web-call page
  GET  /reels.html                  -> "Reels for you" — prioritized story-reel sets
  POST /guide     {text, user_id?, history?[{role,content}], voice?}
                                    -> {ok, reply, refs, safety, guardian?}
  POST /reel-groups {user_id?, text?, themes?[]}
                                    -> {ok, groups:[{priority,title,subtitle,reels[]}], basis}
  POST /resonate  {text, user_id?, history?, event?, targets?}
                                    -> {deliveries(+reel_url), context, policy?, rendered}
"""
import json
import os
import sys
import urllib.parse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resonate.envfile import load_env  # noqa: E402

load_env()  # entrypoint-only .env loading; existing env always wins

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402

from resonate import Engine, EngineConfig  # noqa: E402
from resonate.delivery import render, TARGETS  # noqa: E402
from resonate.guide import ScriptureGuide  # noqa: E402
from resonate.policy import DeliveryPolicy, PolicyConfig  # noqa: E402
from resonate.ratelimit import RateLimiter  # noqa: E402
from resonate.reels import ReelStore  # noqa: E402
from resonate.story import StoryWeaver  # noqa: E402
from resonate.providers.gloo import is_crisis  # noqa: E402
from resonate import tts  # noqa: E402

_CFG = EngineConfig()
_CFG.memory_persist = True  # the live server remembers recurring themes across sessions
ENGINE = Engine(_CFG)
# Chat-tuned restraint: each message is a candidate "seam". The real restraint comes from the
# engine staying silent on non-resonant text + the safety gate + confidence; the short cooldown
# only de-dupes rapid-fire. (See resonate/policy.py.)
POLICY = DeliveryPolicy(PolicyConfig(
    seams={"message", "reflect", "lesson_complete", "struggle", "streak", "session_end", "pause"},
    cooldown_seconds=3, max_per_session=50, min_confidence=0.5,
))
REELS = ReelStore()
WEAVER = StoryWeaver(ENGINE.gloo)
GUIDE = ScriptureGuide(ENGINE)
# fairness on a shared engine: per-user windows for the endpoints that cost
# real resources (Gloo credit, the Kokoro worker). Context isolation itself is
# free — every memory/graph read-write is already keyed by user_id.
LIMITS = RateLimiter({
    "guide": (8, 60),        # conversation turns / minute / user
    "guide_day": (240, 86400),
    "tts": (30, 60),         # sentence renders / minute / user (streaming uses several per reply)
    "reels": (12, 60),
    "story": (6, 60),
})
_PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(_PROJ, "site", "dist")
SRC_WEB_DIR = os.path.join(_PROJ, "web")
EXT_DIR = os.path.join(_PROJ, "integrations", "chatgpt-extension")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def _limited(self, bucket, key) -> bool:
        """True (and a polite 429 already sent) when this user should slow down."""
        if LIMITS.allow(bucket, key):
            return False
        self._send(429, {"ok": False, "rate_limited": True,
                         "retry_after": LIMITS.retry_after(bucket, key),
                         "reason": "a quiet pace keeps the line open for everyone — one moment"})
        return True

    def _send_file(self, path, ctype):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            self._send(404, {"error": "not found"})
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, path):
        self._send_file(path, "text/html; charset=utf-8")

    _MIME = {
        "html": "text/html; charset=utf-8",
        "js": "text/javascript; charset=utf-8",
        "css": "text/css; charset=utf-8",
        "json": "application/json; charset=utf-8",
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
        "svg": "image/svg+xml", "ico": "image/x-icon",
        "woff": "font/woff", "woff2": "font/woff2",
        "glb": "model/gltf-binary", "gltf": "model/gltf+json",
        "mp3": "audio/mpeg", "wav": "audio/wav",
    }

    def _mime(self, name):
        ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
        return self._MIME.get(ext, "application/octet-stream")

    def do_GET(self):
        raw_path, _, query = self.path.partition("?")
        path = raw_path
        q = urllib.parse.parse_qs(query)

        # API endpoints first
        if path == "/health":
            self._send(200, {"ok": True, "mode": ENGINE.config.provider_mode,
                             "targets": list(TARGETS), "tts": tts.available()})
            return
        if path == "/voices":
            self._send(200, {"ok": True, "available": tts.available(), "voices": tts.voices()})
            return
        if path == "/tts":
            self._handle_tts(q)
            return
        if path == "/ext/content.js":
            self._send_file(os.path.join(EXT_DIR, "content.js"), "text/javascript; charset=utf-8")
            return
        if path == "/guide.html":  # the web call — standalone page, not part of the Vite build
            self._send_html(os.path.join(SRC_WEB_DIR, "guide.html"))
            return
        if path == "/reels.html":  # "Reels for you" — same standalone treatment
            self._send_html(os.path.join(SRC_WEB_DIR, "reels.html"))
            return

        # Serve any static file that exists in site/dist — covers JS, CSS, GLB, images, fonts, etc.
        # Strip leading slash, resolve safely (no path traversal)
        rel = path.lstrip("/") or "index.html"
        # Prevent directory traversal
        candidate = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not candidate.startswith(os.path.normpath(WEB_DIR)):
            self._send(403, {"error": "forbidden"})
            return
        if os.path.isfile(candidate):
            self._send_file(candidate, self._mime(candidate))
            return

        # Also serve assets that live next to the standalone pages in web/ (e.g. the
        # chat-page background at /bg/athena.jpg) — same path-traversal guard.
        web_candidate = os.path.normpath(os.path.join(SRC_WEB_DIR, rel))
        if web_candidate.startswith(os.path.normpath(SRC_WEB_DIR)) and os.path.isfile(web_candidate):
            self._send_file(web_candidate, self._mime(web_candidate))
            return

        # SPA fallback: all other paths → index.html (React router handles it)
        index = os.path.join(WEB_DIR, "index.html")
        if os.path.isfile(index):
            self._send_html(index)
        else:
            self._send(404, {"error": "not found"})

    def _handle_tts(self, q):
        voice = (q.get("voice") or ["bella"])[0]
        text = (q.get("text") or [""])[0]
        if not text.strip():
            self._send(400, {"error": "text required"})
            return
        if self._limited("tts", (q.get("uid") or [self.client_address[0]])[0]):
            return
        try:
            wav = tts.synthesize(voice, text)
        except Exception as e:
            # graceful: the panel falls back to the browser's Web Speech voice
            self._send(503, {"error": str(e)[:200], "fallback": "webspeech"})
            return
        self._send_file(str(wav), "audio/wav")

    def do_POST(self):
        path = self.path.split("?")[0]
        if path not in ("/resonate", "/story", "/guide", "/reel-groups"):
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:
            self._send(400, {"error": "bad json: %s" % e})
            return
        if path == "/reel-groups":
            self._handle_reel_groups(data)
            return
        if path == "/guide":
            user = data.get("user_id", "guide_web")
            if self._limited("guide", user) or self._limited("guide_day", user):
                return
            history = data.get("history") or []
            if not isinstance(history, list):
                history = []
            out = GUIDE.reply(data.get("text", ""), user,
                              history=[h for h in history if isinstance(h, dict)],
                              voice=bool(data.get("voice")))
            self._send(200 if out.get("ok") else 400, out)
            return
        if path == "/story":
            self._handle_story(data)
            return
        user = data.get("user_id", "default")
        history = data.get("history") or []
        if not isinstance(history, list):
            history = []
        history = [str(h)[:2000] for h in history][-5:]
        result = ENGINE.resonate(data.get("text", ""), user, history=history)
        for d in result["deliveries"]:
            if d["status"] == "delivered":  # story-reel action for the panel
                d["reel"] = REELS.resolve(d.get("usfm", ""), d.get("translation", "KJV"))
        result["rendered"] = render(result, data.get("targets") or ["vscode"])
        # Delivery Policy: decide whether to actually surface (when the caller passes an 'event').
        event = data.get("event")
        if event:
            held = any(d["status"] == "safety_hold" for d in result["deliveries"])
            delivered = [d for d in result["deliveries"] if d["status"] == "delivered"]
            if held:
                result["policy"] = {"surface": True, "safety": True, "reason": "crisis — show help, never a verse"}
            elif delivered:
                result["policy"] = POLICY.decide(user, event, confidence=delivered[0]["confidence"],
                                                 themes=delivered[0]["beat"]["themes"])
            else:
                result["policy"] = {"surface": False, "reason": "no resonant beat — stay silent"}
        self._send(200, result)

    def _handle_reel_groups(self, data):
        """'Reels for you' — prioritized sets. Themes come from (in order): explicit
        list, the text's beats, the person's series memory (recurring themes), or a
        steady default — so the page always has something honest to show."""
        from resonate.providers.gloo import lexicon_segment
        user = data.get("user_id", "reels_web")
        if self._limited("reels", user):
            return
        text = (data.get("text") or "").strip()
        if text and is_crisis(text):
            self._send(200, {"ok": False, "safety": True,
                             "reason": "crisis input — reels are not the right response"})
            return
        themes = [t for t in (data.get("themes") or []) if isinstance(t, str) and t.strip()]
        basis = "themes"
        if not themes and text:
            beats = lexicon_segment(text)
            themes = beats[0].themes if beats else []
            basis = "text"
        if not themes:
            top = (ENGINE.memory.patterns(user).get("top_themes") or [])
            themes = [t for t, _ in top[:3]]
            basis = "memory"
        if not themes:
            themes, basis = ["comfort", "hope"], "default"
        groups = REELS.groups_for(ENGINE.verses, themes, [], ENGINE.config.translation)
        self._send(200, {"ok": True, "groups": groups, "basis": basis, "themes": themes})

    def _handle_story(self, data):
        """'Your story' — weave the user's moment + the just-delivered verse into one
        vetted biblical narrative. The panel passes the delivery it already holds, so
        nothing is recomputed. Crisis input never gets a story."""
        user = data.get("user_id", "default")
        if self._limited("story", user):
            return
        text = data.get("text", "")
        if is_crisis(text):
            self._send(200, {"ok": False, "safety": True,
                             "reason": "no story for crisis input — help card instead"})
            return
        verse = data.get("verse") or {}
        beat = data.get("beat") or {}
        themes = beat.get("themes") or []
        ctx = data.get("context_themes") or []
        arcs = [t for t, _ in (ENGINE.memory.patterns(user).get("top_themes") or [])[:3]] \
            if hasattr(ENGINE.memory, "patterns") else []
        narrative = WEAVER.select(themes, ctx, arcs, user_id=user)
        if narrative is None:
            self._send(200, {"ok": False, "reason": "no fitting narrative for this moment"})
            return
        try:
            story = WEAVER.compose(text, themes, narrative, verse, user_id=user,
                                   emotion=beat.get("emotion", ""),
                                   memory_note=data.get("memory_note"))
        except ValueError as e:
            self._send(200, {"ok": False, "reason": str(e)})
            return
        self._send(200, {"ok": True, "story": story})

    def log_message(self, *args):
        pass  # quiet


def main():
    host = os.getenv("RESONATE_HOST", "127.0.0.1")
    port = int(os.getenv("RESONATE_PORT") or os.getenv("PORT") or "8765")
    tts.warm()  # load the Kokoro model in the background — first spoken reply lands fast
    print("Resonate engine running on http://%s:%d  (mode=%s)" % (host, port, ENGINE.config.provider_mode))
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
