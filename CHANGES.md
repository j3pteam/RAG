# J3P Advisor — build 2026-09-17-j

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## Read this first

Build `-i` broke the admin panel with a 500. If you have not already:

**Railway → your service → Variables → add `DB_PERSISTENT_CONN=off`.**

The service restarts and the panel comes back on the old connection
behaviour. No deploy needed. Do that before anything else.

---

## What broke, and what this build changes

`-i` did two separate things and shipped them as one. The first was safe;
the second was not, and I should have separated them at the time.

**Safe:** reusing the connection this file opens for its own tables. It is
opened, used and released entirely in `app.py`, so keeping it alive across
requests is this file's business.

**Not safe:** handing `database.py` a connection it did not open, by
pre-populating `g.db_shared_conn`. That module has its own idea of when a
connection begins and ends — it enters and exits the same connection many
times per request — and a connection that arrives already open, from a
different lifecycle, broke it.

I did not have `database.py` when I wrote that, and assumed its contract
from a comment in `app.py`. That was the mistake.

### In this build

- **The `database.py` hook is off by default.** It only runs with
  `DB_REUSE_SHARED_CONN=on`. Leave it off.
- **Reuse never fails a request.** If a persistent connection can't be
  obtained for any reason, the request opens a fresh one — exactly the
  behaviour before `-i` — and logs a warning.
- **Teardown can't raise.** A connection that won't roll back is closed and
  dropped from the store so the next use reconnects, instead of propagating
  out of the teardown handler.

Verified on all three paths: a failed acquisition still serves the request,
a broken connection is closed and dropped without raising, and a fallback
connection is closed rather than retained.

### What you get

About half the win. `document_advisor_map` and the other `app.py`-side
queries stop paying a handshake per request; `list_documents` and the rest
of `database.py`'s work still do. Overview should land somewhere around
1.5–1.8 s rather than 2.6 s.

The rest needs `database.py`. Send me that file and I can either make it
hold its connection the same way, or confirm the hook is safe to switch on
— it is worth roughly another second per page.

---

## Safe to deploy over a broken -i

If `-i` is currently deployed and erroring, this build fixes it whether or
not you set the environment variable. If you did set
`DB_PERSISTENT_CONN=off`, you can remove it after deploying this, or leave
it — with it set, connections behave exactly as they did in `-h`.

---

## From earlier builds today

Per-phase timing with an on-page breakdown when a page exceeds a second
(`-h`). Chevron on the advisor row edge, render time in the sidebar (`-g`).
Advisors page collapsing to one card at a time (`-f`). The advisor on the
page being the advisor that answers, and the voice-sample archive and slug
fixes (`-e` through `-a`).

---

## Installing

Replace `app.py`, commit to `main`. Check `/health` reports
`"version": "2026-09-17-j"`.
