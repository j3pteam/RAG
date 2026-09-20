# J3P Advisor — build 2026-09-20-j

`app.py`, plus the pre-deploy checks. Includes everything from `-i`.

---

## Repeated clicks can no longer start two voices

Speaking a reply is asynchronous: the audio is fetched before anything
plays, and the "is something already speaking?" flag was only set once the
audio fired its `play` event — seconds later, after the fetch.

A second click inside that window passed the check, because nothing *was*
playing yet. So two runs proceeded and two voices spoke over each other. A
third click made it three.

Two things fix it:

**A flag set synchronously, before the first await.** A rapid second click
now sees that this reply is already being prepared, and treats it as stop —
the same as clicking while it plays.

**A run token claimed on entry.** A later click supersedes an earlier run;
when the earlier one's fetch finally returns, it sees it has been superseded
and releases the audio instead of playing it. Checked at every await — the
first piece, each later piece, and the browser-voice fallback.

Verified by modelling the click handler against a slow fetch:

| Sequence | Voices playing at once |
|---|---|
| Three rapid clicks on one reply | 1 |
| Four rapid clicks across two replies | 0 |
| A single click | 1 |

Never two, and a single click still works normally.

---

## From -i and -h

**The voice starts about four times sooner** — the first piece is ~180
characters rather than 700, with later pieces growing to 900.
**New conversation stops the voice**, and players are tracked outside the
DOM so stopping works even after the message is gone.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-j`.
