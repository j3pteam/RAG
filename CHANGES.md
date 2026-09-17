# J3P Advisor — build 2026-09-17-c

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## Why the voice sample disappeared

`save_advisor_voice_sample` did this:

```
DELETE FROM advisor_voice_samples WHERE advisor_slug = ...
INSERT INTO advisor_voice_samples ...
```

Between those two statements the recording existed only in memory. Anything
going wrong in that window — and the exception handler caught errors,
logged a line, and returned `False` without rolling back — destroyed a
sample that took minutes to record and had already been cloned. Every
re-record ran that risk. The error message it printed, "write failed", was
also indistinguishable from a failure that had changed nothing.

### What now happens instead

**Nothing is deleted on save.** It's an upsert: the row is written over in
place, so there is no moment where the advisor has no sample. If the write
fails, the existing recording is untouched, and the log says so explicitly.

**Every replacement is archived first.** Re-recording copies the current
sample — audio included — into `advisor_voice_archive` before writing the
new one. Removing a sample archives it too. The last five per advisor are
kept; audio is large, and the point is undoing a recent mistake rather than
keeping everything forever.

**You can put one back.** Each advisor's Voice Sample section now has a
"Previous recordings (N)" panel listing what was archived, when, and why —
"replaced by a new recording", "removed by an admin". One click restores
it. The sample it displaces is archived in turn, so restoring is itself
undoable. `provider_voice_id` is cleared on restore, because the cloned
voice at ElevenLabs was built from whichever sample was live at the time
and has to be rebuilt from this one.

**The archive works retroactively from now on, not backwards.** It cannot
recover the sample already lost — that one has to be re-recorded. It means
this can't happen again.

### Re-recording Alan's sample

Admin → Advisors → Alan Friedman → Voice Sample. Tick the consent box
before saving; without it nothing is written at all. Aim for one to two
minutes of natural speech — a clip under a minute clones poorly, and that
is the usual cause of a cloned voice that plays but doesn't sound like the
person. There's a suggested script in that section.

Afterwards the section's four-line checklist should read ✓ on all of
sample uploaded, consent given, API key configured, voice cloned. The last
one ticks over on the first use of Speak.

---

## Also in this build

**`/health` reports advisor voice state** (2026-09-17-b). An
`advisor_voice` block lists every advisor, every slug that actually has a
sample, and for each: consent, whether it's cloned, voice mode, size. A
sample filed against a stale slug shows as `"name": "(no advisor with this
slug)"`. `/advisor/speak` also logs the slug it searched and every slug
that does have a sample.

**Preview Voice reports which voice it used and why** (2026-09-17-a).
Every fallback in that handler was previously silent, so a preview that
fell back to the browser voice looked identical to one that worked.

---

## From build 2026-09-16-j

**Admin panel.** Atlassian design language in J3P colours; sentence case
and larger type; contrast-checked status colour on chips and figures. One
tab per request instead of all seven — Overview 553 KB → 71 KB, Advisors →
246 KB. Advisor detail in five bulk queries rather than five per advisor.
Per-advisor participant links with bulk CSV/XLSX upload and export. The
automatic learning toggle merged into Continuous Learning. Copied links are
https.

**Participant chat.** The "Error: Unknown error" bug — the contact scrubber
could delete an entire reply on an advisor's own page, because that
advisor's name was on the staff list. The cloned voice timing out after six
seconds on long replies. The idle prompt interrupting while someone was
typing. The feedback comment box duplicating on a double-tap.

---

## Installing

Replace `app.py`, commit to `main`. Railway rebuilds on push. Check
`/health` reports `"version": "2026-09-17-c"`.

The archive table is created on first use — no migration step.

`admin-atlassian.css` and `admin-refresh.css` in the repo root are dead
files; the CSS is inlined in `ADMIN_HTML`. Safe to delete.
