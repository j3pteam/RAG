# J3P Advisor — build 2026-09-20-o

`app.py`, plus the pre-deploy checks. Includes everything from `-n`.

---

## The internal advisor

Much of this already existed — the database column, the inverted contact
guard, the scrubber bypass, the per-advisor switch, the badges on the page
and in the panel. What was missing was the part that actually makes it
internal.

### What was missing: anyone could open it

The advisor page is decorated `@login_required`, but that only bites when
the global **Sign-in required** setting is on. With that setting off — which
is how it runs — `/a/j3p-internal` was reachable by anyone who knew or
guessed the slug. An advisor that names pricing, staffing, colleagues and
internal email addresses, on an open URL.

A prompt cannot fix that. A prompt does not stop someone opening a page.

**Internal advisors now require a signed-in admin account**, regardless of
any other setting. Closed at three points, not one:

- **The page** — all four advisor routes
- **`/chat`** — otherwise the page could be skipped and the internal slug
  posted straight to the endpoint, which is where the unscrubbed prompt is
  actually built
- **Participant links** — refused at creation *and* again when served, since
  a link is itself a credential and handing one to a client would hand over
  the internal persona

An unauthenticated request gets **the same not-found page as an unknown
advisor**, rather than a "forbidden". A distinct error would confirm to a
stranger that the advisor exists, which is the one fact worth withholding.

### Creating it

**Advisors → Internal J3P advisor → Create the internal J3P advisor.**

One action, because doing it by hand is three steps — create the advisor,
find the internal switch, type INTERNAL — and stopping after the first
leaves a *client-facing* advisor called "J3P Internal", which is the worst
possible outcome. If the flag cannot be set, the advisor is removed again
rather than left in that state.

The section disappears once one exists. Add its knowledge base on the
Knowledge tab as normal.

### Also

The internal flag now has one implementation shared by the creator and the
per-advisor switch, instead of the same UPDATE written twice. The switch's
warning text now says that turning it on stops its existing participant
links working — previously that happened silently.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-o`.

Worth testing: open `/a/j3p-internal` in a private window with no admin
session. You should get the ordinary not-found page.
