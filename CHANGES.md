# J3P Advisor — build 2026-09-20-n

`app.py`, plus the pre-deploy checks. Includes everything from `-m`.

---

## Context questions at the start of a session

Two questions, asked once, before the first message:

- **What is your position?** — Department Chair, Nurse Manager, Program
  Director, and so on
- **What is your area of specialization?** — Orthopaedic Surgery, Nursing,
  Neurosurgery, and so on

Both are free text with a suggestion list attached. Free text on purpose: no
list of titles or specialties is complete, and being absent from a dropdown
is a poor welcome for someone starting a session. The suggestions just save
typing.

Both are optional and the whole thing is skippable, like the personality
survey. When both are switched on, the context questions come first — two
plain factual questions are a gentler opening than a ten-item rating scale —
and each is dismissed separately, so skipping one does not skip the other.

The answers go into the system prompt as a single line, instructing the
advisor to pitch examples, terminology and depth accordingly **without
commenting on it or repeating it back**. An orthopaedic chair and a nurse
manager asking the same question should get different answers, not the same
answer with a preamble about their job.

Stored against the session token rather than the long-lived participant
token, so a fresh visit asks again instead of silently reusing something
answered weeks ago — the same scoping the personality survey uses, and for
the same reason.

## The personality toggle you could not find

It was not there. The setting existed, the save handler existed, the label
existed — but **no checkbox for it was ever rendered in the admin panel**,
so there was no way to turn the survey off short of a code change.

**Settings → Session start** now holds both switches, with a note saying
which are active. Individual advisors can still override either on their own
card in Advisors.

Context questions default to **off**, so nothing changes for participants
until you switch them on.

## American English

You were right, and the "centre" was mine rather than the app's — I will
keep to American spelling.

I checked the app as well and found 31 lines to fix, across prompt text sent
to the model, admin copy, and comments: *organisation, behaviour, colour,
labelled, cancelled, centre, travelling, summarise, acknowledgement, grey*.

One deliberate exception: a scrubber at line 7604 matches both
`behavioral health` and `behavioural health`, because that one reads
*participant* input and has to catch either spelling. Changing it would have
broken the scrubber.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-n`.

To switch the questions on: **Settings → Session start → Ask two context
questions → Save**. The first participant to start a session after that will
see them.
