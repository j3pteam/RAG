# J3P Advisor — build 2026-09-18-d

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## Replies are checked back against the knowledge base

The flow is now **question → retrieval → model → retrieval**.

The first pass was already there: every message is embedded, searched
against the knowledge base, and the matching material is handed to the
model. What was missing is any check that the model *used* it. An answer
can be fluent, on-topic and entirely unsupported, and that is precisely the
failure you cannot spot by reading replies one at a time.

The second pass re-embeds the model's own answer, searches the same
knowledge base with it, and records how well the result backs it up.

| Top similarity | Verdict |
|---|---|
| 0.60 and above | well supported |
| 0.45 to 0.59 | loosely supported |
| below 0.45 | not supported by the knowledge base |
| no chunks returned | nothing in the knowledge base is close |

The threshold sits below the one used for the question itself, deliberately.
A coaching answer legitimately contains framing, structure and phrasing that
appear nowhere in the source documents; demanding the same similarity as a
retrieval query would flag every reply and the signal would be worthless.

### Two decisions worth disagreeing with if you want

**The reply is never changed.** A similarity score is not a good enough
reason to rewrite coaching advice — a rewrite driven by a number would do
more damage than the ungrounded answer it was fixing. The check makes the
pattern visible and leaves the judgement with a person. If you want it to
intervene, that is a different build and worth deciding deliberately.

**It runs after the reply has been sent**, on a background thread. It costs
the participant nothing — no added wait, and a failure in the check can
never affect the conversation it is checking. Given how hard the last two
days of latency work were, spending 1–3 seconds of a participant's time on
a check they never see would have been a poor trade.

### Where to see it

Diagnostics → **Answer grounding**: replies checked, and the split across
well supported, loosely supported and not supported, plus the twelve most
recent with their question, advisor, verdict and score.

Counters are per worker and reset on deploy, so they are indicative. The
record is in the deploy logs — every check writes a `[grounding]` line, at
warning level when a reply is not well supported, with the question and the
source documents that came closest.

**What to do with a run of "not supported":** it usually means the knowledge
base has a gap on that topic rather than that the model invented something.
The recent list names the questions, which is the useful part — those are
the documents worth adding.

---

## From build 2026-09-18-c

The booking button became a setting instead of two URLs: a per-advisor
control (follow the site, always show, always hide) and a per-participant
-link override. Existing `/scheduling` and `/no-scheduling` links still work
and still win.

## From earlier

Conversation log filters staying on Activity (`-b`). The booking button
naming the advisor (`-a`). Queries hoisted out of the render call and gated
by tab (`-m`). Diagnostics tab (`-l`). The advisor on the page being the
advisor that answers, plus the voice-sample work.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-18-d`.

Send a few messages, then open Diagnostics → Answer grounding. If everything
lands in "not supported", tell me the scores — the thresholds are a starting
point calibrated on reasoning, not on your corpus, and they may need moving.
