# J3P Advisor — build 2026-09-21-e

`app.py`, plus the pre-deploy checks (including `urlfor_check.py`).

---

## The default persona now sits under "Client-facing advisors"

It was landing between the internal group and the client-facing heading, so
it read as a third category belonging to neither. It is client-facing — it
is what the main link serves — so the heading now comes first and the card
sits beneath it:

```
Internal — J3P staff only
  J3P Internal

Client-facing advisors
  J3P              (default — used on the main link)
  Alan Friedman
  Bruce Gewertz, MD
```

The same applies when there are no named advisors at all: the heading still
appears, so the default card is never left sitting under "Internal — J3P
staff only".

With no internal advisor, neither heading appears and the page looks exactly
as it always did.

Verified in all three configurations.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-21-e`.
