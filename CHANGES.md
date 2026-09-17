# J3P Advisor — build 2026-09-17-l

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## Diagnostics tab

New item in the sidebar, below Settings, visible to Owner and Admin. It
collects everything that has been chased across this week's debugging into
one place, so the next question starts from data instead of a screenshot.

**This page load** — server time for the request that rendered the page,
with every phase listed in the order it ran. A headline figure coloured by
how bad it is, and a verdict: fast, acceptable, or "slow — the largest
phase below is where to look". Load the tab, read the table.

**Build** — version, what changed in it, and the cold-start cost if this
worker has paid one. A slow first load after a deploy looks identical to a
slow app otherwise.

**Services** — database, embeddings, knowledge base, voice cloning, email.
Each either connected or explicitly not, with the consequence stated
(no API key means Speak uses the browser voice; no email means sign-in
links can't be sent).

**Database connections** — whether connection reuse is on, and whether the
`database.py` sharing that broke build `-i` is enabled. Off by default,
with a note on what it would be worth.

**Advisor voice** — every slug holding a recording, the advisor it belongs
to, consent, whether it has been cloned, mode and size; then the advisors
with no sample. This is the table that would have found the voice
disconnect in one look rather than four rounds.

**Content** — documents, advisors, rated exchanges.

The build number is out of the sidebar. It reads `Admin` and nothing else.

---

## On the speed

Diagnostics will now show the breakdown directly, so the next reading does
not need a screenshot of a sidebar. The last measurements were:

```
2105 ms total
  template render        843 ms
  list_documents         606 ms
  document_advisor_map   536 ms
```

Down from 2606 ms, and still slow. Two things stand between here and fast,
and neither is guesswork any more:

1. **`list_documents` runs through `database.py`**, whose connection is
   still rebuilt on every request. That is most of its 606 ms.
2. **`template render` at 843 ms** is CPU, not database — one large
   template being walked on a small instance.

The first needs `database.py`. I asked for it because guessing at its
connection handling is precisely what took the panel down in `-i`, and I
would rather read it than guess twice.

---

## From earlier today

Timing made opt-in then given a home (`-k`, this build). Connection reuse
made fail-safe after `-i` broke the panel (`-j`). Per-phase timing (`-h`).
Chevron on the advisor row edge (`-g`). Advisors collapsing to one card at a
time (`-f`). The advisor on the page being the advisor that answers, plus
the voice-sample archive, slug labelling and copy-between-advisors work
(`-e` through `-a`).

---

## Installing

Replace `app.py`, commit to `main`. Check the Diagnostics tab reports
version `2026-09-17-l`.
