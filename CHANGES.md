# J3P Advisor — build 2026-09-22-i

`app.py`, the pre-deploy checks, `verify_brand.py`, `brands/`, and the
deployment guides.

---

## An advisor can be a persona of someone outside the firm

Two things were wrong for this case, and neither was visible on the page.

**Every advisor's identity line said "grounded in Alan Friedman's
thinking."** Named advisors add their expertise on top of the core voice,
but the identity underneath stayed yours. Dr. Herbst's team would have met a
J3P advisor wearing his name.

**Every advisor sent people to `clientservices@j3p.health`.** His own
leadership team, asking who to follow up with, would have been routed to
your client services.

Both now follow the advisor:

| | Ordinary advisor | Persona for his team |
|---|---|---|
| Identity | grounded in Alan Friedman's thinking | grounded in Roy S. Herbst, MD, PhD's thinking |
| Referrals | clientservices@j3p.health | their own address |

Set under **Advisors → the advisor → Client branding → Persona of someone
outside J3P**.

## Consent is required, not recommended

The form will not save a persona of a named person without a record of who
confirmed their agreement and when. Refused, not warned about — a warning is
dismissible, and this is the one control standing between a consented
persona and an impersonation.

```
principal set, no consent recorded   -> REFUSED
principal set, consent recorded      -> saved
no principal                         -> saved (ordinary advisor)
```

The record is free text — "Confirmed by email with Dr. Herbst, 22 Sep 2026"
— and is shown on the card afterward. It is a note, not proof, and it is
worth keeping the actual email.

## Setting his up

1. **Advisors → Add or update an advisor** — "Roy S. Herbst, MD, PhD", with
   his photo
2. **Client branding** — Dartmouth's logo and colors
3. **Persona of someone outside J3P** — grounded in his name, referrals to
   his office, consent recorded
4. **Knowledge tab** — his material, assigned to him only
5. **Participant Links** — one per member of his leadership team
6. **Voice Sample** — only with his recorded consent; the voice section
   captures that separately

Their pages will carry Dartmouth's look with a quiet "Delivered by J3P
Health" line, because you are still the firm answering.

## Two things I would settle before it reaches them

**Whose data it is.** His team's transcripts would sit in the same database
as every other client's. For a cancer center's leadership group that is
likely to be asked about, and a separate deployment is the stronger answer —
`NEW_BRAND.md` covers it.

**What it says about him.** The persona answers his team in his name. If it
is grounded in a knowledge base he has not reviewed, it will still speak
confidently as him. Worth him seeing the material before the first
participant link goes out.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-22-i`.
