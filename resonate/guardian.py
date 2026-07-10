"""Guardian alerts — the security module.

When the safety gate holds a crisis, Resonate can (with explicit prior consent)
notify the person's registered guardians by email or WhatsApp. Design rules:

  consent-first  OFF unless RESONATE_GUARDIAN=1 AND the person has guardians
                 registered with "consent": true in data/guardians.json —
                 registration is the person's own act, never automatic.
  privacy-first  the alert NEVER includes what the person typed. It says only
                 that crisis signals appeared and shares the same help lines
                 the person themselves was shown.
  never blocking sends run on a daemon thread; a provider failure can never
                 delay or break the safety card itself.
  rate-limited   one alert per user per cooldown window (default 24 h), so a
                 hard night does not become guardian spam.

guardians.json shape (kept out of git; see data/guardians.example.json):
  {"users": {"<user_id>": {
      "consent": true,
      "display_name": "K.",
      "guardians": [
        {"name": "Mom",  "channel": "email",    "address": "mom@example.com"},
        {"name": "Sam",  "channel": "whatsapp", "address": "+15551234567"}]}}}

Channels: email via stdlib smtplib (SMTP_HOST/PORT/USER/PASSWORD/FROM), WhatsApp
via the Twilio Messages API (TWILIO_SID/TOKEN/TWILIO_WHATSAPP_FROM). Unconfigured
channels log to stderr and are skipped — the module degrades to a no-op, never an error.
"""
from __future__ import annotations

import json
import sys
import threading
import time

ALERT_TEXT = (
    "Resonate safety alert: %s may be going through a difficult moment right now. "
    "This is an automated alert they consented to — what they wrote is private and is "
    "not shared. Please consider reaching out to them personally. "
    "Crisis lines — India: AASRA +91-98204 66726, iCall +91-91529 87821; US: call/text 988."
)


def _log(msg):
    sys.stderr.write("guardian: %s\n" % msg)
    sys.stderr.flush()


class GuardianAlerts:
    def __init__(self, config):
        self.config = config
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- registry
    def _registry(self) -> dict:
        try:
            with open(self.config.guardian_file, encoding="utf-8") as f:
                return json.load(f).get("users", {})
        except (OSError, ValueError):
            return {}

    def _entry(self, user_id: str) -> dict | None:
        e = self._registry().get(user_id)
        if not e or not e.get("consent") or not e.get("guardians"):
            return None
        return e

    # ---------------------------------------------------------------- cooldown
    def _cooldown_path(self):
        return self.config.guardian_file + ".log"

    def _recently_alerted(self, user_id: str) -> bool:
        try:
            with open(self._cooldown_path(), encoding="utf-8") as f:
                last = json.load(f).get(user_id, 0.0)
        except (OSError, ValueError):
            return False
        return (time.time() - float(last)) < self.config.guardian_cooldown_h * 3600

    def _mark_alerted(self, user_id: str):
        data = {}
        try:
            with open(self._cooldown_path(), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            pass
        data[user_id] = time.time()
        try:
            with open(self._cooldown_path(), "w", encoding="utf-8") as f:
                json.dump(data, f)
        except OSError:
            pass

    # ---------------------------------------------------------------- channels
    def _send_email(self, address: str, body: str) -> bool:
        c = self.config
        if not (c.smtp_host and c.smtp_from):
            _log("email skipped (SMTP not configured)")
            return False
        import smtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = "Resonate safety alert — someone you care about may need you"
        msg["From"] = c.smtp_from
        msg["To"] = address
        msg.set_content(body)
        with smtplib.SMTP(c.smtp_host, c.smtp_port, timeout=20) as s:
            s.starttls()
            if c.smtp_user:
                s.login(c.smtp_user, c.smtp_password)
            s.send_message(msg)
        return True

    def _send_whatsapp(self, address: str, body: str) -> bool:
        c = self.config
        if not (c.twilio_sid and c.twilio_token and c.twilio_whatsapp_from):
            _log("whatsapp skipped (Twilio not configured)")
            return False
        import httpx
        r = httpx.post(
            "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json" % c.twilio_sid,
            auth=(c.twilio_sid, c.twilio_token),
            data={"From": "whatsapp:%s" % c.twilio_whatsapp_from,
                  "To": "whatsapp:%s" % address, "Body": body},
            timeout=20)
        r.raise_for_status()
        return True

    def _dispatch(self, entry: dict):
        body = ALERT_TEXT % (entry.get("display_name") or "someone you registered with Resonate")
        for g in entry.get("guardians", []):
            try:
                sent = (self._send_whatsapp if g.get("channel") == "whatsapp"
                        else self._send_email)(g.get("address", ""), body)
                _log("%s -> %s: %s" % (g.get("channel"), g.get("name", "?"),
                                       "sent" if sent else "skipped"))
            except Exception as e:  # one guardian failing must not stop the rest
                _log("%s -> %s failed: %s" % (g.get("channel"), g.get("name", "?"), str(e)[:120]))

    # ---------------------------------------------------------------- public
    def alert(self, user_id: str) -> dict:
        """Called by the engine when the safety gate holds. Returns a small status
        dict for the delivery payload (transparency: the person is told when their
        guardians were pinged). The actual sends happen on a daemon thread."""
        if not self.config.guardian_enabled:
            return {"enabled": False}
        entry = self._entry(user_id)
        if entry is None:
            return {"enabled": True, "registered": 0, "dispatched": False}
        with self._lock:
            if self._recently_alerted(user_id):
                return {"enabled": True, "registered": len(entry["guardians"]),
                        "dispatched": False, "reason": "cooldown"}
            self._mark_alerted(user_id)
        threading.Thread(target=self._dispatch, args=(entry,), daemon=True).start()
        return {"enabled": True, "registered": len(entry["guardians"]), "dispatched": True}
