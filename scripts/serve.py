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
_CFG.yv_cache_persist = True  # and caches verse text to disk so grounding never waits on YouVersion
# guardian alerts on by default now that there's a registration UI — still a no-op unless a
# person has registered consenting guardians AND SMTP/Twilio creds exist (else it just logs).
_CFG.guardian_enabled = True
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


def _read_guardians():
    try:
        with open(ENGINE.config.guardian_file, encoding="utf-8") as f:
            return json.load(f).get("users", {})
    except (OSError, ValueError):
        return {}


def _write_guardians(users):
    path = ENGINE.config.guardian_file
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"users": users}, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
# fairness on a shared engine: per-user windows for the endpoints that cost
# real resources (Gloo credit, the Kokoro worker). Context isolation itself is
# free — every memory/graph read-write is already keyed by user_id.
LIMITS = RateLimiter({
    "resonate": (20, 60),    # panel lookups / minute / user (each costs Gloo + YouVersion)
    "guide": (8, 60),        # conversation turns / minute / user
    "guide_day": (240, 86400),
    "tts": (30, 60),         # sentence renders / minute / user (streaming uses several per reply)
    "reels": (12, 60),
    "story": (6, 60),
})

# "Carry this moment to Ezra" hand-off: the popup POSTs the moment here and the guide
# page collects it ONCE — so the person's words never ride in a URL (browser history,
# server logs). In-memory only, single-read, short-lived.
_HANDOFF = {}          # uid -> (text, expires_at)
_HANDOFF_TTL = 180.0


def _handoff_put(uid, text):
    import time
    now = time.time()
    for k in [k for k, (_, exp) in _HANDOFF.items() if exp < now]:
        _HANDOFF.pop(k, None)
    if uid and text:
        _HANDOFF[uid] = (text[:1200], now + _HANDOFF_TTL)


def _handoff_take(uid):
    import time
    text, exp = _HANDOFF.pop(uid, (None, 0))
    return text if exp >= time.time() else None
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
                             "translation": ENGINE.config.translation,
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
        if path == "/connect.html":  # "Connect to your assistant" (MCP onboarding)
            self._send_html(os.path.join(SRC_WEB_DIR, "connect.html"))
            return
        if path == "/guardians.html":  # consent-first guardian registration
            self._send_html(os.path.join(SRC_WEB_DIR, "guardians.html"))
            return
        if path == "/guardians":  # GET current registration for a uid (their own data)
            uid = (q.get("uid") or [""])[0]
            reg = _read_guardians().get(uid, {}) if uid else {}
            self._send(200, {"ok": True, "registration": reg})
            return
        if path == "/handoff":  # single-read pickup of a moment the popup handed over
            self._send(200, {"ok": True, "text": _handoff_take((q.get("uid") or [""])[0])})
            return
        if path in ("/resonate", "/story", "/guide", "/reel-groups"):
            # POST-only API paths: answer plainly instead of falling through to the SPA
            self._send(405, {"error": "use POST", "path": path})
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
        # Umbrella: a bug or a network outage inside any handler must surface as a JSON
        # error the panel can show — never a dropped connection (observed live when the
        # machine's DNS blipped mid-pipeline).
        try:
            self._do_POST()
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                self._send(502, {"ok": False, "error": "engine hiccup: %s" % str(e)[:160],
                                 "retryable": True})
            except OSError:
                pass  # client already gone

    def _do_POST(self):
        path = self.path.split("?")[0]
        if path not in ("/resonate", "/story", "/guide", "/reel-groups", "/guardians", "/handoff"):
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:
            self._send(400, {"error": "bad json: %s" % e})
            return
        if path == "/handoff":
            _handoff_put(str(data.get("user_id") or ""), str(data.get("text") or ""))
            self._send(200, {"ok": True})
            return
        if path == "/reel-groups":
            self._handle_reel_groups(data)
            return
        if path == "/guardians":
            self._handle_guardians_save(data)
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
        text = data.get("text", "")
        event = data.get("event")
        crisis = is_crisis(text)
        # Policy pre-gate: when cooldown/budget already forbids surfacing, don't spend
        # the LLM calls the decision would suppress. Crisis text NEVER takes this exit —
        # the safety card must always render, whatever the policy state.
        if event and not crisis:
            pre = POLICY.precheck(user, event)
            if not pre["surface"]:
                self._send(200, {"user_id": user, "deliveries": [],
                                 "series_memory": ENGINE.memory.patterns(user),
                                 "context": {"history_messages": len(data.get("history") or []),
                                             "themes": []},
                                 "rendered": {}, "policy": pre})
                return
        # crisis text is also exempt from rate limiting — help must ALWAYS render
        if not crisis and self._limited("resonate", user):
            return
        history = data.get("history") or []
        if not isinstance(history, list):
            history = []
        history = [str(h)[:2000] for h in history][-5:]
        result = ENGINE.resonate(text, user, history=history)
        # Chat surfaces (they pass an 'event') get at most ONE verse per message — a
        # two-beat message must not stack two panels. Transcripts (playground, no event)
        # keep every beat. Safety holds always survive the cut.
        if data.get("event"):
            delivered = [d for d in result["deliveries"] if d["status"] == "delivered"]
            if len(delivered) > 1:
                best = max(delivered, key=lambda d: d["confidence"])
                result["deliveries"] = [d for d in result["deliveries"]
                                        if d["status"] != "delivered" or d is best]
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

    def _handle_guardians_save(self, data):
        """Save a person's own guardian registration (consent-first). This is the person
        editing their OWN entry on their OWN engine — the alert itself never shares what
        they typed; guardians only get a 'reach out to them' nudge (see resonate/guardian.py)."""
        uid = (data.get("user_id") or "").strip()
        if not uid:
            self._send(400, {"ok": False, "error": "user_id required"})
            return
        raw = data.get("guardians") or []
        guardians, problems = [], []
        for g in raw[:5]:
            name = str(g.get("name", "")).strip()[:60]
            channel = "whatsapp" if g.get("channel") == "whatsapp" else "email"
            address = str(g.get("address", "")).strip()[:120]
            if not (name and address):
                continue  # a blank row is just an unused row
            ok = ("@" in address) if channel == "email" else address.replace("+", "").replace(" ", "").isdigit()
            if not ok:
                # A typo here must NEVER silently become "no guardians" — for a safety
                # feature, tell the person exactly which entry to fix.
                problems.append("%s: %s" % (name, "email needs an @" if channel == "email"
                                            else "phone must be digits with +countrycode"))
                continue
            guardians.append({"name": name, "channel": channel, "address": address})
        if problems:
            self._send(400, {"ok": False, "error": "check " + "; ".join(problems),
                             "invalid": problems})
            return
        users = _read_guardians()
        if not guardians:                       # empty save = withdraw consent / remove
            users.pop(uid, None)
        else:
            users[uid] = {"consent": bool(data.get("consent")),
                          "display_name": str(data.get("display_name", "")).strip()[:40] or "someone",
                          "guardians": guardians}
        try:
            _write_guardians(users)
        except OSError as e:
            self._send(500, {"ok": False, "error": str(e)[:120]})
            return
        entry = users.get(uid, {})
        self._send(200, {"ok": True, "count": len(entry.get("guardians", [])),
                         "consent": entry.get("consent", False)})

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
    if hasattr(ENGINE.yv, "warm"):  # pre-fetch corpus verse text so grounding never waits on YouVersion
        import threading as _th
        _th.Thread(target=lambda: ENGINE.yv.warm([v["usfm"] for v in ENGINE.verses.verses]),
                   daemon=True).start()
    print("Resonate engine running on http://%s:%d  (mode=%s)" % (host, port, ENGINE.config.provider_mode))
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
