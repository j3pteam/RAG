# J3P Advisor — build 2026-09-17-i

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## Why the admin panel was slow

The breakdown on the Overview page gave it away:

```
2606 ms total
  list_documents          1043 ms
  document_advisor_map     817 ms
  template render          564 ms
  feedback stats + log      91 ms
```

A 30-row select taking a second, and two tiny lookups taking another. The
SQL is not what costs that. Each was the **first use of a separate database
connection**, and the app opened both fresh on every request — TCP, TLS and
auth against a remote managed Postgres, roughly a second each, paid before
any query ran. Around 1.9 s of every page load was handshake.

An earlier round of this made each connection shared for the duration of a
single request, which removed dozens of extra handshakes *within* a page.
It did nothing about the two that happened again on the *next* page, and
the phase marks were too coarse to show that.

### The fix

Connections now live for the life of the worker rather than the request.
One set per thread, so the background learning scheduler never shares with
a request; gunicorn's sync workers handle one request at a time, so within a
worker this is a single connection with no contention.

At the end of a request they are rolled back and handed back rather than
closed — the rollback clears anything left open, so the next request starts
clean.

This also covers `database.py`'s own connection, without modifying that
file: it caches on `g.db_shared_conn` and opens one if absent, so a
`before_request` hook populates it with the thread's live connection.

Dead connections are handled: managed Postgres drops idle ones, and the
rollback on handover is what detects that. A broken connection is discarded
and replaced on next use.

Set `DB_PERSISTENT_CONN=off` to revert to per-request connections without a
deploy, if anything looks wrong.

**Expected:** the first page load after a deploy still pays both handshakes.
Every page after that should drop by roughly 1.9 s. If Overview comes back
around 600–700 ms, that is the handshake gone and the remaining time is the
template render, which is the next thing to look at.

### The timing display

That breakdown in the sidebar is mine — it appears only when a page takes
over a second, so once this is fixed it should disappear on its own. If you
want it gone regardless, delete the `_with_render_time` call sites or set
`SLOW_PAGE_MS` to a large number.

---

## From build 2026-09-17-h

Per-phase timing, and the on-page breakdown when a page exceeds a second.

## From 2026-09-17-g and -f

Chevron pinned to the row edge; render time beside the build number.
Advisors page collapses to one card at a time.

## From build 2026-09-17-e

**The advisor on the page is the advisor that answers** — a stored
participant link was overriding the page, so the voice and the replies came
from a different advisor than the one shown. Plus voice samples showing
their slug and copyable between advisors, no longer destroyed on save, and
archived and restorable.

## From build 2026-09-16-j

Admin panel rebuilt on the Atlassian design language in J3P colours; one
tab per request; per-advisor participant links with bulk upload and export.
Participant chat: the "Error: Unknown error" bug, the cloned voice timeout,
the idle prompt interrupting typing, the duplicate feedback box.

---

## Installing

Replace `app.py`, commit to `main`. Railway rebuilds on push. Check
`/health` reports `"version": "2026-09-17-i"`.

`admin-atlassian.css` and `admin-refresh.css` in the repo root are dead
files; the CSS is inlined in `ADMIN_HTML`. Safe to delete.
