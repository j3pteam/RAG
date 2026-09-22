# J3P Advisor — build 2026-09-21-i

`app.py`, plus the pre-deploy checks (including `urlfor_check.py`).

---

## What your numbers say so far

```
2847 ms total
  list_documents          504 ms
  list_advisors          1309 ms   ← dominant
  feedback stats + log     66 ms
  settings                248 ms
  page-specific lookups   622 ms
  template render          98 ms
```

I checked `list_advisors` first, because 1309 ms for five advisors looks
like a query problem. **It is not.** That query already selects
`(photo IS NOT NULL)` rather than the photo bytes, returns five rows, and
has no join. There is nothing in it that takes a second.

Nor is it an N+1 loop: every per-advisor lookup on that page is already one
query covering all advisors at once. I confirmed that before writing any of
this.

That leaves one explanation consistent with the shape of these numbers —
several phases each in the hundreds of milliseconds, on trivial queries.
**The time is in reaching the database, not in the work it does.**

## So this build separates the two

The timing panel now reports connection opens as their own line:

```
list_advisors                                1309 ms
settings                                      248 ms
[of which: opening 2 database connections]    990 ms
```

Every physical `psycopg.connect` is counted and timed, on both the
persistent path and the fallback. It appears in the panel and in the
`[timing]` log line beside the phases it was hiding inside.

**Load the Advisors tab and read that line.** It decides between two very
different fixes:

- **Large (most of the page)** — the database is being reached over the
  public proxy, and connections are not surviving between requests. The fix
  is the `DATABASE_PRIVATE_URL` environment variable, which costs nothing
  and needs no code. Check what Diagnostics → Database connections reports
  for the address; if it is not a `.railway.internal` host, that is the
  whole answer.
- **Small or absent** — connections are being reused properly and the time
  really is in the queries, which means I have something specific to
  optimize and will need the row to say which.

I would rather send you one line to read than another build that guesses.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-21-i`.
