# J3P Advisor — build 2026-09-17-k

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## The timing panel is gone from the page

It was a diagnostic and it had no business sitting in the sidebar
permanently. The sidebar now reads `build 2026-09-17-k` and nothing else.

It still exists when it is wanted: add `?timing=1` to any admin URL, e.g.

```
web-production-901d85.up.railway.app/admin?tab=overview&timing=1
```

and the breakdown appears under the build number for that load only. The
measurement also continues to go to the Railway logs on every request as a
`[timing]` line, so nothing was lost by hiding it.

---

## Where the numbers stand

Overview went from 2606 ms to **2105 ms** with the safe half of the
connection reuse. Latest breakdown:

```
template render        843 ms
list_documents         606 ms
document_advisor_map   536 ms
feedback stats + log    60 ms
```

Two observations worth recording:

**`template render` is now the largest single item.** The template compiles
once per worker and is cached, so 843 ms is the render itself walking a
large template. That is a CPU cost on a small instance, not a database one,
and it would need a different fix from everything done so far — most
likely splitting `ADMIN_HTML` so a tab's markup is not parsed when another
tab is being served.

**`list_documents` and `document_advisor_map` are still 500–600 ms each.**
They were ~1000 and ~800 before, so connection reuse helped, but not as
much as it should have. `list_documents` goes through `database.py`, whose
connection is still rebuilt per request — that part is expected. That
`document_advisor_map` is still 536 ms is not, since it uses the reused
connection, and it suggests the per-query cost against this database is
genuinely high rather than being handshake alone.

Both point at the same next step: send me `database.py` and I can stop
guessing at its connection handling, which is what broke build `-i`.

---

## From build 2026-09-17-j

Connection reuse made fail-safe. The `database.py` hook that broke `-i` is
off unless `DB_REUSE_SHARED_CONN=on`; reuse failures fall back to opening a
fresh connection; teardown cannot raise.

## From earlier today

Per-phase timing (`-h`). Chevron on the advisor row edge (`-g`). Advisors
page collapsing to one card at a time (`-f`). The advisor on the page being
the advisor that answers, plus the voice-sample archive, slug labelling and
copy-between-advisors work (`-e` through `-a`).

---

## Installing

Replace `app.py`, commit to `main`. Check `/health` reports
`"version": "2026-09-17-k"`.

If you set `DB_PERSISTENT_CONN=off` while `-i` was broken, it is safe to
remove now — but leaving it costs only the connection reuse, nothing else.
