# J3P Advisor — build 2026-09-21-c

`app.py`, plus the pre-deploy checks (including `urlfor_check.py`).

---

## No booking button on an internal advisor

"Schedule time with J3P Internal" is meaningless — there is no such person
to book — and it is exactly the sort of thing that ends up in a screenshot.

An internal advisor now never shows the booking button, whatever the site
setting, the per-advisor override, or the `/scheduling` variant of the link
says. Enforced at render rather than set as a default when the advisor is
created, so it also covers an advisor switched to internal later, and a
stray click on its card cannot undo it.

`/a/j3p-internal` is therefore already the link without scheduling.

## Pinned to the top and set apart

Internal advisors now sort above every client-facing card, under their own
heading, with a dark red left border and tint:

```
Internal — J3P staff only
  [J3P Internal]

Client-facing advisors
  [Alan Friedman]
  …
```

Verified by rendering with the internal advisor deliberately **second** in
the input — it still comes out first, with the headings falling in the right
places.

They behave differently from every other card on that page — different
naming rules, different access, no booking button — so mixing them in
alphabetically invites someone to treat one like the rest.

## The knowledge base

It was already correct, and the card was not saying so. An internal advisor
reads the **shared J3P knowledge base** — every document with no advisor
assignment, which is exactly what the default advisor reads. Documents
assigned to a named advisor stay with that advisor.

Two changes so the page tells the truth:

- The **Knowledge-Base Portal** section is gone for internal advisors. A
  portal is a self-service link for a person to manage their own documents.
  An internal advisor is not a person and has no separate base — offering
  one invites building a second knowledge base that nothing would read.
- Its **Knowledge** section now states plainly that it answers from the
  shared J3P base, the same documents the default advisor uses, "without a
  separate base to keep in step".

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-21-c`.
