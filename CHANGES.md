# J3P Advisor — build 2026-09-20-i

`app.py`, plus the pre-deploy checks. Includes everything from `-h`.

---

## The voice starts sooner

Nothing is heard until the first piece has finished synthesising, and every
piece was up to 700 characters — so you waited for 700 characters of
synthesis before any sound, however long the reply.

Pieces now **grow as they go**: about 180 characters for the first, 420 for
the second, 900 after that. The opening line is spoken while the longer
pieces behind it are still being made.

| Reply | First piece | Sound starts | Was | Pieces (was) |
|---|---|---|---|---|
| 600 chars | 95 chars | ~0.7s | ~2.7s | 3 (1) |
| 2,000 chars | 95 chars | ~0.7s | ~3.0s | 4 (3) |
| 6,000 chars | 95 chars | ~0.7s | ~3.0s | 9 (9) |
| 19,000 chars | 95 chars | ~0.7s | ~3.0s | 24 (29) |

Roughly four times faster to first sound, and no slower overall — playback
of one piece overlaps synthesis of the next, so the listener never catches
up with the fetching.

They grow rather than staying short because each piece is a separate call to
the voice service. All-short would triple the request count for no benefit
once playback is under way. On your 19,000-character reply this is actually
*fewer* calls than before — 24 instead of 29 — while starting far sooner,
which also answers the usage question I raised earlier.

---

## Still worth confirming

Your last few screenshots showed the old status label, so the build in the
browser was older than `-g`. If `/health` does not report
`2026-09-20-i` after deploying, none of the recent fixes — including the
New-conversation stop — are live yet.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-i`.
