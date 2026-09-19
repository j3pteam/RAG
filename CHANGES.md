# J3P Advisor — build 2026-09-19-a

One file: `app.py`. Deploy this to fix the failed deployment.

---

## Why the deploy failed

Build and Deploy both passed. It died at **Network → Healthcheck** after
23 seconds.

`railway.json` points the healthcheck at `/health` with a 30-second budget.
That makes `/health` the very first request a fresh container serves —
before psycopg or voyageai have been imported, before any connection
exists, before the schema check has run.

In build `2026-09-17-b` I added an `advisor_voice` block to that endpoint.
It runs two database queries and ensures two tables. On a warm database it
answers in time; on a cold one it does not, and the deploy fails.

The endpoint already carried this comment, three lines below what I added:

> *Deliberately env-only: calling `db.is_enabled()` here imported psycopg
> and voyageai on the very first request, which is the healthcheck — the
> reason deploys were failing.*

So this was diagnosed and fixed once before, written down in the right
place, and I broke it again anyway. That explains the intermittency too —
`-c` through `-g` deployed because the timing happened to fall inside the
window.

## The fix

`/health` now calls nothing but `jsonify`, `os.environ.get` and `bool`.
Verified by walking the function's syntax tree: no database-touching call
remains.

Nothing is lost. The advisor voice report moved to the admin panel under
**Diagnostics** in build `-l`, which is a page a person loads, not a
liveness probe with a deadline.

The comment on the endpoint is now explicit about the rule rather than
describing a past incident, so the next person to reach for it — including
me — sees the constraint before the history.

---

## Everything else is unchanged from -g

PubMed and OpenAlex literature search in the Knowledge tab. Session
transcripts scopeable to assigned advisors. Participant text kept out of
the deploy logs. Replies checked back against the knowledge base.

---

## Installing

Replace `app.py`, commit to `main`. The deploy should pass its healthcheck
this time; `/health` should return quickly and report version
`2026-09-19-a`.

If it fails again at the same step, the cause is something else and the
deploy log will name it — send me what "View logs" shows.
