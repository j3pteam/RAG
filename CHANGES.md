# J3P Advisor — build 2026-09-19-h

`app.py`, plus the pre-deploy checks.

---

## Found it: the database is on the public network

The Diagnostics reading settles this:

```
3317 ms
  list_advisors        1341 ms   ← first use of one connection
  list_documents        893 ms   ← first use of the other
  page-specific lookups 665 ms
  settings              266 ms
  feedback stats + log   68 ms   ← two queries, connection already open
  template render        84 ms
```

**Two queries on an open connection: 68 ms. Two queries that each open a
connection: 2.2 seconds.** The database is fast. Connecting to it is what
costs, and roughly a second per handshake is not TCP and TLS to a machine
in the same datacentre — that is a round trip over the public internet.

Railway exposes a Postgres service two ways:

- `DATABASE_URL` — a **public proxy** hostname, something like
  `roundhouse.proxy.rlwy.net`. Traffic leaves the datacentre and comes
  back.
- a **private** `.railway.internal` address, which does not leave.

If your web service is using the first, every connection pays an internet
round trip. That is consistent with every number measured this week,
including why removing two-thirds of the queries barely moved the total.

## What this build does

It prefers the private address automatically. If `DATABASE_PRIVATE_URL` is
set, it is used — including by `database.py`, because the value is placed
into the environment before either module reads it, so no change to that
file is needed.

**Diagnostics now names the address** under Database connections:

```
Database address   postgres.railway.internal
                   private network — connections stay local
```

or

```
Database address   roundhouse.proxy.rlwy.net
                   public proxy — every connection leaves the datacentre,
                   costing roughly a second
```

Only the hostname is shown, never the URL — it carries the password.

## What you need to do

In Railway, on the **web** service → Variables, add:

```
DATABASE_PRIVATE_URL = ${{Postgres.DATABASE_PRIVATE_URL}}
```

using the variable-reference syntax so Railway fills it in. (The exact name
on the Postgres service may differ — look for the one whose host ends in
`.railway.internal`.) Leave the existing `DATABASE_URL` alone; it stays as
a fallback.

**Expected result:** connection time drops from ~1000 ms to single digits.
On the numbers above, the Diagnostics page would go from 3317 ms to roughly
400 ms, and Activity proportionally.

If Diagnostics still says "public proxy" after that, the variable did not
resolve, and the hostname shown will say which one it got.

---

## From -g

`?timing=1` works on every tab, not just Diagnostics — which is how this
was finally measured.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-19-h`, and its Database connections section will tell you which
network you are on.
