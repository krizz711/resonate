# Multi-user: one context graph per person

> "There will be many users — how do we keep a separate context graph per user?"

The whole engine is already **partitioned by `user_id`**. Every write and every query
takes a `user_id` and only ever touches that person's slice — recency, theme-fatigue,
narrative arcs, series memory. Two users are never in the same graph; there is no shared
state to leak. So the question is really two smaller ones: *how does each person keep a
stable id across surfaces?* and *how does the store stay correct and fast when thousands
hit it at once?*

## 1. The id — one person, every surface

`user_id` is the partition key. Each surface carries a **stable id for the same human**,
and they hand it to each other so it's the *same* id everywhere:

| Surface | Where the id lives | How it's shared |
|---|---|---|
| ChatGPT extension | `chrome.storage.sync.userId` (`chat_…`) | appended as `?uid=` when it opens Ezra/Reels |
| Ezra chat/call (`guide.html`) | `localStorage.resonate_uid` | reads `?uid=` first, else its stored id |
| Reels (`reels.html`) | `localStorage.resonate_uid` | same — reads `?uid=` handoff |
| MCP (Claude/ChatGPT/…) | `user_id` tool argument | the host assistant passes it per call |

So a person who meets Resonate in ChatGPT and then taps through to Ezra keeps **one
graph** — Ezra can say "you've been circling weariness lately" because the extension's
theme events and Ezra's are the same `user_id`. No login, no PII: the id is a random
handle, and **only themes are stored, never the text anyone typed**.

*(A true account/login would unify ids across devices too — a clean future upgrade, not
needed for the demo.)*

## 2. The store — correct and scalable under load

`resonate/memory.py` has one interface, two backends (factory: `make_memory`):

### LocalMemory (default)
In-process `dict` keyed by `user_id`, optional atomic JSON snapshot. The server is a
`ThreadingHTTPServer`, so many users are served on many threads at once — every write and
every read is guarded by an `RLock` and reads compute on a **snapshot** of the user's
list, so concurrent writes can't corrupt state or raise mid-iteration. Proven by
`TestMemory.test_concurrent_writes_are_safe` (12 threads × 50 writes, interleaved reads,
zero errors, zero lost events) and `test_users_are_isolated`.

Good for the demo and any single-node deploy. Limits: it's one process's RAM + one JSON
file, so it doesn't share across instances and grows with total users.

### RedisMemory (production, flip a switch)
The same graph as namespaced Redis keys — `resonate:events:<user_id>` (a capped list) and
`resonate:episode:<user_id>` (a counter). Redis handles concurrency server-side and
persists across restarts, and the log is `LTRIM`-capped (500 events/user) so a heavy user
can't grow unbounded. Because both backends derive their queries from the **same** pure
function (`_derive`), behaviour is identical — the engine doesn't know or care which is
active.

Turn it on with two env vars; nothing else changes:

```
RESONATE_MEMORY=redis
REDIS_URL=redis://default:<password>@<host>:<port>
```

Free tier is plenty to start (Redis Cloud / Upstash). **If the package isn't installed or
the server is unreachable, `make_memory` logs it and falls back to LocalMemory** — a bad
Redis URL can never take Resonate down.

## Scaling picture

```
              many users, each a random resonate_uid
                              │
        ┌──────────┬──────────┼───────────┬───────────┐
   ChatGPT ext   Ezra call   Reels page   MCP host   VS Code
        └──────────┴──────────┼───────────┴───────────┘
                   POST /guide, /reresonate, /reel-groups …
                              │  (user_id on every call)
                     Resonate engine  (stateless per request)
                              │
                    make_memory(user_id-partitioned)
                       ┌──────┴───────┐
                 LocalMemory      RedisMemory     ← one node → many nodes
                 (RLock, JSON)    (Redis Cloud)      just by env flag
```

The engine itself keeps no per-user state between requests — all continuity lives in the
memory backend under `user_id` — so you scale by running more stateless engine processes
behind Redis. No sticky sessions, no shared mutable globals.
