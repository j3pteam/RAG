# J3P Advisor — build 2026-09-24-d

`app.py`, the pre-deploy checks, `verify_brand.py`, `brands/`, and the
deployment guides.

---

## The consent record no longer blocks

It was never real protection, and I should have weighed that before making
it a hard stop. It is a free-text box — anyone can type anything into it —
so refusing to create the engagement bought no actual safeguard while
standing between you and your own setup.

The field stays, and so does the note:

> Naming a real person makes this advisor speak as a voice grounded in their
> thinking, to people who may report to them. Worth having their agreement
> before it does — this box is somewhere to note when and how, not a
> requirement.

What protects the named person is the agreement itself. A form cannot check
that, and pretending it can is worse than saying so.

Removed from both places it applied: the Add Client form and the persona
form on an existing engagement.

## The logo uploads with the engagement

A **Their logo** field now sits in the same form. One step means one step —
telling you to come back and upload it afterward was a second step wearing a
different name.

The file is validated **before anything is created**. A rejected logo would
otherwise leave a half-set-up advisor behind, which is the exact state this
route exists to prevent — so a wrong file type, an empty file or one over
2 MB stops the whole thing with nothing written. When it is accepted, the
logo is stored in the same transaction as the branding and persona fields.

Optional, and still replaceable later under Current engagements.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-d`.
