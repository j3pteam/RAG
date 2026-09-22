# J3P Advisor — build 2026-09-21-h

`app.py`, plus the pre-deploy checks (including `urlfor_check.py`).

---

## Admin page times, in Diagnostics

"The admin panel is slow" has come round several times and every round has
been guesswork, because the phase breakdown only ever existed in the deploy
logs or behind `?timing=1` — neither of which is in front of the person who
notices the slowness.

**Diagnostics → Admin page times** now shows the last twelve admin pages
loaded, newest first:

```
22:56:04  /admin?tab=advisors  3.12s  list_advisors 180ms ·
          personality map 290ms · behavioral map 310ms · 360 map 280ms ·
          voice map 300ms · briefings 270ms · participant links 620ms ·
          documents 410ms · template render 340ms
```

Every map is timed separately, so the breakdown names the culprit rather
than lumping them together.

**Load the Advisors tab, then open Diagnostics, and tell me what the row
says.** That turns this into one specific fix.

## What I checked, so we do not repeat it

I looked for the obvious cause first. All five per-advisor lookups —
personality, behavioral, 360, voice, briefings — are already **one query
each for every advisor at once**. There is no N+1 loop hiding on that tab,
which was my first suspicion and is wrong.

What that leaves, and what the numbers will distinguish between:

- **Many phases each a few hundred ms** — that is per-connection overhead,
  about nine round trips on that tab. It points back at the database being
  reached over the public proxy, which the Diagnostics section above already
  reports, and at `DB_REUSE_SHARED_CONN` still being off.
- **One phase dominating** — a specific query to fix.
- **template render large** — the page itself, not the database.

These have different fixes, and right now I cannot tell them apart from
here.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-21-h`.
