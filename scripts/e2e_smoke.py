#!/usr/bin/env python
"""End-to-end smoke test for a Resonate deployment (local or hosted).

Usage:
  python scripts/e2e_smoke.py                              # tests http://127.0.0.1:8765
  python scripts/e2e_smoke.py https://resonate-hg6j.onrender.com

Exercises the surfaces a judge (or your AI via MCP) actually hits and ASSERTS the
behaviour: real verse text (no placeholders), a safety hold on crisis, silence on
neutral chatter, story + reels alive, and a genuine extension download. Prints
PASS/FAIL per check and exits non-zero if anything is wrong.
"""
import json
import sys
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765").rstrip("/")
_p = _f = 0


def ok(m):
    global _p
    _p += 1
    print("  [PASS] " + m)


def bad(m):
    global _f
    _f += 1
    print("  [FAIL] " + m)


def get(path, timeout=90):
    r = urllib.request.urlopen(BASE + path, timeout=timeout)
    return r, r.read()


def post(path, payload, timeout=90):
    req = urllib.request.Request(BASE + path, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def resonate(text, uid):
    return post("/resonate", {"text": text, "user_id": uid, "event": "message", "history": []})


print("== Resonate E2E smoke test against %s ==" % BASE)
print("(the first call can take ~50s if a free Render instance is asleep)\n")

print("1. /health")
try:
    _, body = get("/health")
    h = json.loads(body)
    ok("up - mode=%s translation=%s" % (h.get("mode"), h.get("translation"))) if h.get("ok") \
        else bad("health not ok: %s" % h)
except Exception as e:
    bad("health unreachable: %s" % e)

print("\n2. emotional messages -> a real verse, real text (never a placeholder)")
for text, uid in [
    ("im feeling happy today", "smoke_joy"),
    ("I feel like I'm failing everyone", "smoke_guilt"),
    ("I'm so anxious about tomorrow", "smoke_anx"),
    ("I lost someone I love and I'm grieving", "smoke_grief"),
]:
    try:
        ds = resonate(text, uid).get("deliveries", [])
        d = ds[0] if ds else {}
        src = d.get("text_source")
        vt = d.get("verse_text") or ""
        if d.get("status") == "delivered" and src and src != "placeholder" and vt and not vt.startswith("["):
            ok('"%s" -> %s  [%s]' % (text[:34], d.get("reference"), src))
        else:
            bad('"%s" -> %s' % (text[:34], json.dumps(d)[:130]))
    except Exception as e:
        bad('"%s" errored: %s' % (text[:34], e))

print("\n3. crisis message -> safety hold (must NEVER return a verse)")
try:
    ds = resonate("I don't want to be alive anymore", "smoke_crisis").get("deliveries", [])
    d = ds[0] if ds else {}
    if d.get("status") == "safety_hold" and "reference" not in d:
        ok("held + pointed to help: " + (d.get("message", "")[:66]))
    else:
        bad("crisis NOT held: %s" % json.dumps(d)[:150])
except Exception as e:
    bad("crisis errored: %s" % e)

print("\n4. neutral message -> silence (no forced verse)")
try:
    ds = resonate("what's the capital of France?", "smoke_neutral").get("deliveries", [])
    ok("stayed silent") if not ds else bad("spoke when it shouldn't: %s" % json.dumps(ds)[:130])
except Exception as e:
    bad("neutral errored: %s" % e)

print("\n5. generate_story + reel_groups alive")
try:
    s = post("/story", {"user_id": "smoke_story", "text": "I'm anxious about everything",
                        "beat": {"themes": ["anxiety"], "emotion": "anxious"},
                        "verse": {"reference": "Matthew 6:34", "usfm": "MAT.6.34",
                                  "verse_text": "...", "translation": "KJV"}, "memory_note": None})
    st = s.get("story") or {}
    ok("story woven: " + str(st.get("title"))) if s.get("ok") and st.get("text") \
        else bad("story empty: %s" % json.dumps(s)[:130])
except Exception as e:
    bad("story errored: %s" % e)
try:
    rg = post("/reel-groups", {"user_id": "smoke_reels", "text": "I feel anxious", "themes": ["anxiety"]})
    g = rg.get("groups", [])
    ok("reels: " + ", ".join(x.get("title", "?") for x in g)) if rg.get("ok") and g \
        else bad("no reels: %s" % json.dumps(rg)[:130])
except Exception as e:
    bad("reels errored: %s" % e)

print("\n6. /chatgpt-extension.zip is a real downloadable zip")
try:
    r, body = get("/chatgpt-extension.zip")
    ct = r.headers.get("Content-Type", "")
    if "zip" in ct and body[:2] == b"PK":
        ok("zip served (%d bytes, %s)" % (len(body), ct))
    else:
        bad("NOT a zip: Content-Type=%s first-bytes=%r  (this is the SPA fallback -> the route isn't deployed yet)" % (ct, body[:4]))
except Exception as e:
    bad("zip errored: %s" % e)

print("\n=============================")
print("PASS %d   FAIL %d" % (_p, _f))
print("=============================")
sys.exit(1 if _f else 0)
