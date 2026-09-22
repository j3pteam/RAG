# J3P Advisor — build 2026-09-22-b

`app.py`, plus the pre-deploy checks (including `urlfor_check.py`).

---

## What I found in the review

I looked for repeated work rather than tidiness. Two things were doing the
same query several times per request.

**`get_advisor` had 30 call sites and no cache.** A single reply reaches
about six of them — the scheduling decision, the contact guard, the voice
guard, the internal-access check, the log write — each its own SELECT and
its own round trip, all returning the same row. An advisor cannot change in
the middle of a request.

**`document_advisor_map` ran on every chat turn**, to filter retrieval
results, and repeatedly while the admin panel builds the Advisors and
Knowledge tabs. It only changes when a document is reassigned.

Both are now memoized on `flask.g` — per request, not per process — so an
edit is visible on the very next request rather than served stale. Both
memos are dropped explicitly after any write that would invalidate them,
so a redirect that re-reads within the same request sees the change.

## What that is worth

Round trips per reply: **13 → 8**.

| Latency per round trip | Before | After | Saved |
|---|---|---|---|
| 15 ms (private network) | 0.20s | 0.12s | 0.07s |
| 120 ms | 1.56s | 0.96s | 0.60s |
| 250 ms (public proxy) | 3.25s | 2.00s | 1.25s |

**Which row you are on is the whole question**, and it is the one thing I
still cannot see from here. If you are on the bottom row this saves over a
second per reply; if you are on the top it saves almost nothing, because
the time is elsewhere.

## What I checked and left alone

- **Settings** are already cached process-wide.
- **Retrieval** already computes one embedding and uses it for both the
  knowledge search and the lessons lookup.
- The apparent duplicate `log_interaction` and `append_history` calls are on
  the safety-response branch, which returns early — not double work.
- The five per-advisor admin lookups are already one query each for all
  advisors; no N+1.

So the chat path is not doing obviously wasteful work beyond what I fixed.
That points the remaining time at the model call and the network path to the
database — neither of which is code cleanliness.

**Diagnostics → Reply times still has the answer**, and it was empty when
you last looked because no reply had been handled by that worker since the
deploy. Send one message, reload Diagnostics, and the row will say whether
the model call dominates.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-22-b`.
