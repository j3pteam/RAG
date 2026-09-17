# J3P Advisor — build 2026-09-17-a

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## This build: Preview Voice now tells you what it did

Preview played the browser voice while "Alan Friedman's own voice" was
selected, and said nothing about why. Every fallback path in that handler
was silent — a bare `catch`, and a 204 response carrying an
`X-Voice-Status` header that nothing read. So a preview that fell back was
indistinguishable from one that worked.

The menu footnote is now the preview's status line:

- **Playing Alan Friedman's own voice.** — it worked
- **Using the default reading voice — no voice sample has been uploaded for them yet.**
- **... — their voice sample has no consent on record.**
- **... — voice cloning isn't configured on the server.**
- **... — they're set to the default voice in the admin panel.**
- **... — the voice service returned an error — ElevenLabs HTTP 401: ...**
- **... — their voice took too long to generate.**
- **The browser blocked playback — click Preview again.**

That last one is worth knowing about: the click's user-gesture allowance can
expire while waiting for synthesis, and the browser then refuses to start
audio. It was previously caught and discarded, indistinguishable from a
server-side failure. It's the one case a participant can fix themselves.

Click Preview and read the line underneath. It will name the reason.

If it says the sample has no consent, or none is uploaded, that's in the
admin panel under the advisor's Voice Sample section — its checklist shows
all four conditions. If it reports an ElevenLabs error, the message carries
the provider's own response.

---

## Installing

Replace `app.py`, commit to `main`. Railway rebuilds on push. Check
`/health` reports `"version": "2026-09-17-a"`.

---

## Included from the previous build (2026-09-16-j)

**Admin panel.** Rebuilt on the Atlassian design language in J3P colours;
sentence case and larger type throughout; status colour on chips and figures
with every pairing checked for contrast. One tab per request instead of all
seven — Overview went from 553 KB to 71 KB, Advisors to 246 KB. Advisor
detail reads in five bulk queries rather than five per advisor. Per-advisor
participant links with bulk CSV/XLSX upload and export. The automatic
learning toggle merged into the Continuous Learning card. Copied links are
https.

**Participant chat.** The "Error: Unknown error" bug — the contact scrubber
could delete an entire reply on an advisor's own page, because that
advisor's name was on the staff list. The cloned voice timing out after six
seconds on long replies. The idle prompt interrupting while someone was
typing. The feedback comment box duplicating on a double-tap.

---

## Worth deleting while you're in there

`admin-atlassian.css` and `admin-refresh.css` in the repo root are drafts
from before the CSS was inlined into `ADMIN_HTML`. Nothing loads either.
