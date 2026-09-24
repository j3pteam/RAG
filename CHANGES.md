# J3P Advisor — build 2026-09-24-a

`app.py`, the pre-deploy checks, `verify_brand.py`, `brands/`, and the
deployment guides.

---

## Add Client is its own tab

Managing your own coaches and standing up a client engagement are different
jobs, and the client tooling was cluttering every advisor card — including
the four it will never apply to.

**Admin → Add Client** now holds all of it. The Advisors tab is back to what
it was: profiles, photos, links, knowledge, voice.

## Set up a client in one step

Name, organization, whose thinking it is grounded in, where participants are
sent, and the two colors — one form, one save.

Done as separate forms this is four saves, and stopping after the first
leaves an advisor named for a client **still wearing J3P's branding and
speaking as Alan Friedman**. That is worse than not having started, and it
is exactly what happens when someone is interrupted halfway. Either the
whole engagement exists or none of it does: if any part of the setup fails,
the advisor is removed again rather than left in that state.

Validated before anything is created — a colour that is not six-digit hex, a
referral address with no `@`, or a named person with no consent record all
stop the whole thing with nothing written.

## Current engagements

Below the form, each client engagement with its session link, whose voice it
speaks in, where participants are sent, the logo upload, the branding fields
and the persona fields.

Roy Herbst appears here as soon as his branding or persona is set — the list
is derived from the advisor actually carrying a client's branding or a
persona, not from a separate flag. An advisor cannot be listed as an
engagement while carrying none of the things that make it one.

Your own coaches — Alan, Bruce, David — stay out of this tab entirely.

## One thing I had to fix to make it work

`list_advisors()` did not return any of the branding or persona fields, so
the "is this a client engagement?" test would have been false for everyone
and the tab would have looked permanently empty. Caught by rendering it, not
by reading it.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-a`.

Roy Herbst's existing profile will appear under Add Client once you set his
organization, colors or persona — until then he is an ordinary advisor,
which is what he currently is.
