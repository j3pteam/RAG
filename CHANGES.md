# J3P Advisor — build 2026-09-24-c

`app.py`, the pre-deploy checks, `verify_brand.py`, `brands/`, and the
deployment guides.

---

## Found it, and your two screenshots are what found it

Two things in them settled a question I have been guessing at for days.

**No "opening N database connections" line appeared.** That line only shows
when a physical connection is opened, so connections are being reused and
the network handshake is *not* the cost. Every earlier theory of mine that
blamed the public proxy was wrong.

**`list_advisors` was 1870 ms on Overview and 121 ms on Diagnostics.** The
same query, 15× apart, moments apart. A query does not vary like that. What
varies is whether something else happened alongside it.

## What was happening

Every table has an "ensure" function that creates it and adds any columns
introduced since. Each `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` is a round
trip **whether or not it does anything**, and the advisors table had
accumulated 24 of them as features were added — several of them mine, this
week.

They run once per worker, on its first request. So:

- the first page load a worker handles pays all 24
- it happens again on every redeploy, and every time Railway cycles a worker
- the *second* load looks fine, which is why it never reproduced when I
  looked for it

1870 ms was the first request on that worker. 121 ms was what the query
actually costs.

## The fix

One query to `information_schema` asking which columns exist, then only the
ALTERs genuinely missing:

| Situation | Round trips |
|---|---|
| Everything already there — the normal case | **1** |
| Two columns missing, after a new feature | 3 |
| Fresh database | 22 |
| **Before this change, every time** | **24** |

Applied to the advisors and chat_history tables, which are the two that had
grown.

The columns are now a single list in one place, which also means adding one
is a one-line change rather than another ALTER appended to a pile.

## What is left

`list_documents` is steady at 456–492 ms across both loads. That is
`database.py`, the one file in this project I have never had. If you send
it, that is the next 450 ms.

`page-specific lookups` at 605 ms on Diagnostics is the diagnostics queries
themselves, which only that tab pays.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-c`.

The very first load after deploying still pays the old cost once per worker
— it is the load that runs the new migration. From the second onward it
should be steady.
