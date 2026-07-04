"""Live-API preflight — run this the moment competition keys arrive (2026-07-06).

  1. copy .env.example -> .env, paste GLOO_CLIENT_ID / GLOO_CLIENT_SECRET /
     YOUVERSION_APP_KEY  (and accept your Bible's license on platform.youversion.com)
  2. pip install httpx
  3. python scripts/live_check.py

It validates the whole live chain step by step with PASS/FAIL lines:
Gloo OAuth token -> Gloo completion -> YouVersion bible catalog (resolves the
KJV bible id for RESONATE_BIBLE_ID) -> passage fetch -> full engine end-to-end.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resonate.envfile import load_env  # noqa: E402

load_env()

from resonate.config import EngineConfig  # noqa: E402

PASS = "  [PASS] "
FAIL = "  [FAIL] "
_failures = []


def step(name):
    print("\n== %s" % name, flush=True)


def ok(msg):
    print(PASS + msg, flush=True)


def bad(msg, hint=""):
    print(FAIL + msg, flush=True)
    if hint:
        print("         hint: " + hint, flush=True)
    _failures.append(msg)


def main():
    cfg = EngineConfig()
    cfg.provider_mode = "live"

    step("0. environment")
    gloo_ready = bool(cfg.gloo_client_id and cfg.gloo_client_secret)
    if gloo_ready:
        ok("Gloo client credentials present")
    else:
        print("  [SKIP] Gloo credentials not set yet (challenge keys open 2026-07-06) — "
              "running the YouVersion-only checks.")
    if cfg.yv_app_key:
        ok("YouVersion app key present")
    else:
        bad("YOUVERSION_APP_KEY missing",
            "platform.youversion.com -> your application -> app key; put it in .env")
    try:
        import httpx  # noqa: F401
        ok("httpx installed")
    except ImportError:
        bad("httpx not installed", "pip install httpx")
    if _failures:
        return finish()

    from resonate.providers.gloo import LiveGloo
    from resonate.providers.youversion import LiveYouVersion
    gloo = LiveGloo(cfg)
    yv = LiveYouVersion(cfg)

    if gloo_ready:
        step("1. Gloo OAuth2 token exchange")
        try:
            tok = gloo._access_token()
            ok("access token obtained (%d chars, ~1h lifetime)" % len(tok))
        except Exception as e:
            bad("token exchange failed: %s" % e,
                "check client id/secret; endpoint = %s/oauth2/token" % cfg.gloo_base_url)
            return finish()

        step("2. Gloo chat completion (auto_routing)")
        try:
            out = gloo._chat("Reply with exactly one word: ready.", "ping", temperature=0.0)
            ok("completion returned: %r" % out.strip()[:60])
        except Exception as e:
            bad("completion failed: %s" % e)

    step("3. YouVersion bible catalog (resolve bible id)")
    bible_id = cfg.bible_id
    try:
        data = yv.list_bibles("eng")
        items = data.get("data") or data.get("bibles") or (data if isinstance(data, list) else [])
        ok("catalog returned %d English bibles" % len(items))
        want = (cfg.translation or "KJV").upper()
        # exact match first, then prefix (the catalog uses year-suffixed abbreviations,
        # e.g. NIV -> "NIV11", NASB -> "NASB2020"); prefer the shortest candidate.
        abbrs = [(str(b.get("abbreviation", "")).upper(), b) for b in items]
        match = next((b for a, b in abbrs if a == want), None)
        if match is None:
            pref = sorted([(len(a), a, b) for a, b in abbrs if a.startswith(want)])
            if pref:
                match = pref[0][2]
        if match:
            bible_id = str(match.get("id", ""))
            found = match.get("abbreviation", want)
            ok("%s resolved -> %s (bible id %s)" % (want, found, bible_id))
            if not cfg.bible_id:
                print("         put this in .env:  RESONATE_BIBLE_ID=%s" % bible_id)
        else:
            names = ", ".join(sorted(str(b.get("abbreviation", "?")) for b in items)[:20])
            bad("%s not in your catalog" % want,
                "accept its license on platform.youversion.com (Licensing) — available now: %s" % names)
    except Exception as e:
        bad("catalog failed: %s" % e,
            "note: /v1/bibles requires language_ranges[] (we send it) and an app key with accepted licenses")

    step("4. YouVersion passage fetch (JHN.3.16, format=text)")
    if bible_id:
        cfg.bible_id = bible_id
        try:
            got = yv.fetch("JHN.3.16")
            ok("%s: %r" % (got["translation"], got["text"][:80]))
        except Exception as e:
            bad("passage fetch failed: %s" % e)
    else:
        bad("skipped — no bible id resolved")

    if gloo_ready:
        step("5. Engine end-to-end in LIVE mode")
        try:
            from resonate import Engine
            eng = Engine(cfg)
            res = eng.resonate("I'm so anxious about tomorrow, I can't stop worrying.", "live_check")
            d = next((x for x in res["deliveries"] if x["status"] == "delivered"), None)
            if d and d["text_source"] == "youversion":
                ok("verse delivered from live YouVersion: %s — %r" % (d["reference"], d["verse_text"][:60]))
                ok("bridge (live Gloo): %r" % d["bridge"][:80])
            elif d:
                bad("verse delivered but text_source=%s (expected youversion)" % d["text_source"])
            else:
                bad("no verse delivered — inspect deliveries: %s" % [x["status"] for x in res["deliveries"]])
        except Exception as e:
            bad("end-to-end failed: %s" % e)
    else:
        step("5. Engine end-to-end — SKIPPED until Gloo keys arrive (July 6)")

    return finish()


def finish():
    print("\n" + "=" * 56)
    if _failures:
        print("LIVE CHECK: %d failure(s) — fix the hints above and re-run." % len(_failures))
        return 1
    print("LIVE CHECK: ALL GREEN — set RESONATE_MODE=live in .env and restart scripts/serve.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
