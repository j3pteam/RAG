# J3P Advisor — build 2026-09-17-m

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## "template render" was not rendering

The Diagnostics reading was:

```
1629 ms
  template render        841 ms
  list_documents         488 ms
  document_advisor_map   179 ms
  feedback stats + log    61 ms
  list_advisors           60 ms
```

841 ms to render is implausible — the template compiles once per worker and
is cached after that. It turned out that phase was not measuring rendering.
Six database calls sat in the *argument list* of the render call:

```python
html = _cached_render(
    ADMIN_HTML,
    settings=load_settings(force=True),        # a query
    avatar_custom=avatar_exists(),             # a query
    briefings=list_briefings(...),             # a query
    admin_identity=current_admin_identity(),   # a query
    diag={"voice": _voice_health()},           # two queries
    ...
```

Python evaluates those before the call runs, so they were counted as
render. The measurement was honest about the total and wrong about the
cause, which is exactly the failure mode of a coarse phase mark.

They are hoisted out now and timed separately. More importantly, hoisting
them made obvious that most are not needed on most tabs.

## Queries gated by tab

| Tab | Before | After |
|---|---|---|
| Settings | 15 | 3 |
| Overview | 15 | 4 |
| Biometric | 15 | 4 |
| Users | 15 | 5 |
| Knowledge | 15 | 5 |
| Diagnostics | 15 | 6 |
| Advisors | 15 | 8 |
| Activity | 15 | 9 |

What changed:

- **`list_documents` — the 488 ms one — now runs only on tabs that show or
  count documents.** Activity, Settings, Users and Biometric never looked at
  it and were paying for it on every load.
- **`document_advisor_map`** (179 ms) runs only for Knowledge and Advisors.
- **`avatar_exists`** only for Advisors, **`list_briefings`** only for
  Activity, **`current_admin_identity`** only for Users and Diagnostics.
- **`_voice_health`** re-queried the advisor list the route had already
  loaded; it takes it as an argument now.

At roughly 60–180 ms per round trip against this database, Overview should
land near 400–500 ms and Settings lower still. Advisors and Activity stay
heaviest because they genuinely need the data.

Reload Diagnostics after deploying and the table will show where it
actually stands.

---

## What is left after this

If the remaining figure is still higher than you want, two things are
known and neither is guesswork:

1. **Each query costs 60–180 ms.** That is round-trip latency to Postgres,
   not query cost — the tables are small. Reducing it further means fewer
   round trips, or a database closer to the app.
2. **`list_documents` goes through `database.py`**, whose connection is
   still rebuilt per request. That file is the one piece of this I have
   never seen; guessing at its connection handling is what took the panel
   down in build `-i`.

---

## From earlier today

Diagnostics tab (`-l`). Timing made opt-in (`-k`). Connection reuse made
fail-safe (`-j`) after it broke the panel (`-i`). Per-phase timing (`-h`).
Chevron on the advisor row edge (`-g`). Advisors collapsing to one card at a
time (`-f`). The advisor on the page being the advisor that answers, plus
the voice-sample archive and slug work (`-e` through `-a`).

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-17-m`.
