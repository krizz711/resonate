# Resonate — Discord connector

*Scripture as conversation, not broadcast.* A second delivery surface for the Resonate engine,
proving the "you choose where Scripture meets you" architecture. It follows a channel's flow and
gently replies with a verse **only when someone's words echo one** — and **never** on a crisis
(it points to help instead). The same engine + Delivery Policy power it as the ChatGPT and
VS Code surfaces.

## Try it offline (no token, no install)
```bash
python integrations/discord/bot.py --selftest
```
Shows what the bot would post for a vulnerable message (a verse), an ordinary one (silence),
a crisis (a help message), and gratitude.

## Run it live
```bash
pip install -r integrations/discord/requirements.txt
export DISCORD_TOKEN=your-bot-token     # Windows: $env:DISCORD_TOKEN="..."
python integrations/discord/bot.py
```
Enable the **Message Content Intent** in the Discord developer portal for your bot.

## How it fits
`bot.py` is thin: a `reply_for(user, text)` function (pure, unit-tested) calls
`resonate.responder.Responder`, which runs the engine, applies the Delivery Policy (restraint),
routes crises to help, and formats with the `discord` delivery target. Swapping surfaces is just
swapping the target. See [`../../ENGINE-DESIGN.md`](../../ENGINE-DESIGN.md).
