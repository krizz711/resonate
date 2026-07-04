"""Local Resonate engine server (Python standard library only).

A tiny JSON HTTP API the connectors (ChatGPT extension, VS Code, web panel, Discord) call.

Run:  python scripts/serve.py     ->  http://127.0.0.1:8765
Endpoints:
  GET  /health                      -> {ok, mode, targets, tts}
  GET  /voices                      -> {ok, available, voices:[{id,label}...]}
  GET  /tts?voice=bella&text=...    -> audio/wav (Kokoro + godly preset) | 503 {fallback}
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
from resonate.policy import DeliveryPolicy, PolicyConfig  # noqa: E402
from resonate.reels import ReelStore  # noqa: E402
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
_PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(_PROJ, "web")
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

    def do_GET(self):
        raw_path, _, query = self.path.partition("?")
        path = raw_path
        q = urllib.parse.parse_qs(query)
        if path in ("/", "/index.html"):
            self._send_html(os.path.join(WEB_DIR, "index.html"))
        elif path.endswith(".html"):
            self._send_html(os.path.join(WEB_DIR, os.path.basename(path)))  # basename avoids traversal
        elif path == "/ext/content.js":  # for web/mock-chat.html — runs the real content script
            self._send_file(os.path.join(EXT_DIR, "content.js"), "text/javascript; charset=utf-8")
        elif path == "/health":
            self._send(200, {"ok": True, "mode": ENGINE.config.provider_mode,
                             "targets": list(TARGETS), "tts": tts.available()})
        elif path == "/voices":
            self._send(200, {"ok": True, "available": tts.available(), "voices": tts.voices()})
        elif path == "/tts":
            self._handle_tts(q)
        else:
            self._send(404, {"error": "not found"})

    def _handle_tts(self, q):
        voice = (q.get("voice") or ["bella"])[0]
        text = (q.get("text") or [""])[0]
        if not text.strip():
            self._send(400, {"error": "text required"})
            return
        try:
            wav = tts.synthesize(voice, text)
        except Exception as e:
            # graceful: the panel falls back to the browser's Web Speech voice
            self._send(503, {"error": str(e)[:200], "fallback": "webspeech"})
            return
        self._send_file(str(wav), "audio/wav")

    def do_POST(self):
        if self.path.split("?")[0] != "/resonate":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:
            self._send(400, {"error": "bad json: %s" % e})
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

    def log_message(self, *args):
        pass  # quiet


def main():
    host = os.getenv("RESONATE_HOST", "127.0.0.1")
    port = int(os.getenv("RESONATE_PORT", "8765"))
    print("Resonate engine running on http://%s:%d  (mode=%s)" % (host, port, ENGINE.config.provider_mode))
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
