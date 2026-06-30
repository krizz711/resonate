"""Resonate — Discord connector. Scripture as conversation, not broadcast.

Reuses the *same* engine + Delivery Policy as every other surface. It follows the flow of a
channel and, only when someone's words echo a verse (and never on a crisis), gently replies
in-thread. Silent the rest of the time.

  Live:    set DISCORD_TOKEN, then:  python integrations/discord/bot.py
  Offline: python integrations/discord/bot.py --selftest   (no token, no discord.py needed)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from resonate.responder import Responder  # noqa: E402

RESPONDER = Responder(target="discord")


def reply_for(user_id, text):
    """Pure logic — what (if anything) the bot should post. No discord dependency, so it's
    unit-testable and offline-demoable."""
    r = RESPONDER.respond(str(user_id), text)
    if not r["surface"]:
        return None
    if r["kind"] == "help":
        return r["text"]
    msg = r["rendered"]["content"]
    if r.get("memory_note"):
        msg += "\n*(" + r["memory_note"] + ")*"
    return msg


def selftest():
    print("Resonate Discord connector — offline self-test\n" + "-" * 52)
    samples = [
        ("user_a", "I feel like I'm failing everyone lately and I can't keep up."),
        ("user_b", "what's the capital of France?"),
        ("user_c", "honestly I do not want to live anymore"),
        ("user_d", "I'm so grateful — today was a real gift."),
    ]
    for uid, text in samples:
        out = reply_for(uid, text)
        print('\nUSER: "%s"' % text)
        print("BOT : %s" % (out if out else "(stays silent)"))


def run_bot():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("No DISCORD_TOKEN set. Try:  python integrations/discord/bot.py --selftest")
        return
    import discord  # lazy import — only needed to actually connect

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print("Resonate connected as", client.user)

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        out = reply_for(message.author.id, message.content)
        if out:
            await message.channel.send(out)

    client.run(token)


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else run_bot()
