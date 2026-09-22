# J3P Advisor — build 2026-09-21-f

`app.py`, plus the pre-deploy checks (including `urlfor_check.py`).

---

## An internal session starts straight in the conversation

Three client-entry gates are gone for an internal advisor:

- **Release & Acknowledgment.** It is a liability waiver for someone
  receiving coaching. Asking a J3P colleague to release J3P from liability
  before they can ask about pricing is both odd and legally pointless.
- **Personality survey.** Ten rating items to tailor coaching to a client.
- **Position and specialization questions.** Added yesterday to pitch
  replies at a client's level. A colleague's role is not what this advisor
  needs to know.

The scheduling overlay goes with them, since an internal advisor has no
booking button to reach it.

Opening `/a/j3p-internal` now lands directly in the conversation with the
composer ready.

## Decided server-side, not hidden in the page

Both intake flags are set to false in the render call rather than the markup
merely being left out. The page reads flags that are actually false, so
there is no half-state where an overlay is absent but the entry chain is
still waiting on it — which is exactly the sort of thing that would leave a
composer permanently blocked.

Verified: with every overlay absent the entry chain still unblocks the
composer and focuses the message box. Client-facing pages are unchanged —
all four gates still present.

## One thing I left alone

The small footer lines are still there:

> For informational purposes only. Not official advice.
> The J3P Advisor is AI and can make mistakes. Please double-check
> responses.

The second is true for a colleague as much as a client. The first is
client-facing language and I can drop it for internal sessions if you want —
I did not, because you named the modal rather than the footer, and removing
an accuracy caveat felt like the wrong thing to assume.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-21-f`.
