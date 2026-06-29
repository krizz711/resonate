"""Local Resonate engine server (Python standard library only).

A tiny JSON HTTP API the connectors (VS Code extension, future web panel, Discord bot) call.

Run:  python scripts/serve.py     ->  http://127.0.0.1:8765
Endpoints:
  GET  /health                      -> {ok, mode, targets}
  POST /resonate  {text, user_id?, targets?, translation?}
                                    -> {deliveries, series_memory, rendered:{target:[...]}}
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402

from resonate import Engine, EngineConfig  # noqa: E402
from resonate.delivery import render, TARGETS  # noqa: E402

ENGINE = Engine(EngineConfig())
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


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

    def _send_html(self, path):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            self._send(404, {"error": "not found"})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send_html(os.path.join(WEB_DIR, "index.html"))
        elif path == "/health":
            self._send(200, {"ok": True, "mode": ENGINE.config.provider_mode, "targets": list(TARGETS)})
        else:
            self._send(404, {"error": "not found"})

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
        result = ENGINE.resonate(data.get("text", ""), data.get("user_id", "default"))
        result["rendered"] = render(result, data.get("targets") or ["vscode"])
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
