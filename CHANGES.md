# J3P Advisor — build 2026-09-21-g

`app.py`, plus the pre-deploy checks (including `urlfor_check.py`).

---

## The internal card now shows only what applies to it

Gone from that card: **Voice Sample**, **Onboarding**, and **Pre-Call
Briefings** (with the Activity heading that only held it).

Each was not merely unused but misleading:

- A **voice sample** clones a real person's voice. An internal advisor is
  not a person — leaving the section there invites someone to upload Alan's
  voice to it.
- **Onboarding** records a real person's assessments, so its counter would
  have read 0/2 forever, looking like something left undone.
- **Pre-call briefings** are prepared when someone books time through an
  advisor's link. An internal advisor has no booking button, so the section
  could only ever be empty.

**Knowledge stays**, since that is the one thing on the card that does apply
— and it now explains that it reads the shared J3P base.

## The chips said the wrong thing too

The summary row read:

```
0 PARTICIPANT LINKS · 0 DOCUMENTS · ONBOARDING 0/2 ·
NO VOICE SAMPLE · NO PORTAL LINK
```

Five things reported as absent, reading like five things left undone, when
none of them apply. Replaced with two that are true:

```
Reads the shared J3P knowledge base · Admin sign-in required
```

Client-facing cards keep every section and chip. Confirmed card by card in
the render test.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-21-g`.
