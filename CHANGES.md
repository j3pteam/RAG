# J3P Advisor — build 2026-09-17-b

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## The voice problem

Preview now reports: **"no voice sample has been uploaded for them yet."**

That is the server saying there is no row in `advisor_voice_samples` for
slug `alan-friedman`. It is a database fact, not a display bug — and the
white-label work did not cause it. That work added code to
`synthesize_advisor_voice` (a cache and two log lines) and changed nothing
else in the voice path; `get_advisor_voice_meta`, `save_advisor_voice_sample`,
`set_advisor_voice_provider`, `_advisor_voice_ensure_table` and the
`/advisor/speak` route are byte-identical to the build before it.

Three things produce that message, and they need different fixes:

1. **The sample was never saved.** The upload requires the consent checkbox;
   without it nothing is written, and the form does not always make that
   obvious.
2. **It was saved, then removed.** Re-recording replaces the row, and
   "Remove sample" deletes it.
3. **It is filed under a different slug** than the participant page asks
   for — e.g. the advisor was renamed, which changes the slug, leaving the
   sample attached to the old one.

### Finding out which

Open `/health` on the deployment. There is now an `advisor_voice` block:

```json
"advisor_voice": {
  "elevenlabs_key_set": true,
  "advisors": ["alan-friedman", "bruce-gewertz"],
  "with_sample": {
    "alan-friedman": {
      "name": "Alan Friedman",
      "consent_given": true,
      "cloned": true,
      "voice_mode": "participant_choice",
      "size_kb": 2929
    }
  },
  "advisors_without_sample": ["bruce-gewertz"]
}
```

- `alan-friedman` absent from `with_sample` → case 1 or 2: re-record it in
  the admin panel under Advisors → Alan Friedman → Voice Sample, and tick
  the consent box before saving.
- A slug in `with_sample` showing `"name": "(no advisor with this slug)"` →
  case 3. The sample is orphaned against an old slug. Re-record under the
  current advisor.
- Present with `consent_given: false` → the sample exists but is unusable.
  The Voice Sample section has a "Confirm consent for this recording"
  form that fixes it without re-recording.
- Present and correct but `elevenlabs_key_set: false` → the sample is fine
  and the provider is not configured.

`/advisor/speak` also logs the slug it searched and every slug that does
have a sample, so the Railway logs show the same thing.

### While you are in there

The admin panel's Voice Sample section for each advisor has a four-line
checklist — sample uploaded, consent given, API key configured, voice
cloned. If Alan's shows ✗ on the first line, that confirms case 1 or 2
immediately.

A note on sample length: a clip under a minute clones poorly, and that is
the most common cause of a cloned voice that plays but does not sound like
the person. Aim for one to two minutes of natural speech.

---

## Also in this build (2026-09-17-a)

Preview Voice reports which voice it used and why. Every fallback path in
that handler was previously silent — a bare `catch`, and a 204 response
carrying an `X-Voice-Status` header that nothing read — so a preview that
fell back to the browser voice looked identical to one that worked. The
footnote under the button now names the reason, including the case where
the browser blocks playback because the click's gesture allowance expired
during synthesis, which the participant can fix by clicking again.

---

## From build 2026-09-16-j

**Admin panel.** Atlassian design language in J3P colours; sentence case and
larger type; status colour on chips and figures, contrast-checked. One tab
per request instead of all seven — Overview 553 KB → 71 KB, Advisors → 246
KB. Advisor detail in five bulk queries rather than five per advisor.
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
`/health` reports `"version": "2026-09-17-b"`.

`admin-atlassian.css` and `admin-refresh.css` in the repo root are dead
files — the CSS is inlined in `ADMIN_HTML`. Safe to delete.
