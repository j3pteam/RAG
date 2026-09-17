# J3P Advisor — build 2026-09-17-f

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## Advisors page: one card open at a time

Five advisors, each with seven expandable sections and three group captions
between them, produced a page that was mostly scaffolding. Every advisor was
fully expanded whether or not you were working on them.

**Each advisor is now a single collapsed row** — photo, name, slug, status
chips. That is the job the chips were added for, and it is enough to scan a
roster at a glance. Clicking one opens it; opening another closes the first,
so only one advisor's detail is ever on screen. A chevron on the right
shows a card can be opened, and the row highlights on hover.

**"Add or update an advisor" collapses too.** It is a rare action that was
permanently occupying the top of the page. One line until you need it.

**Tighter spacing throughout.** The Profile / Links / Setup captions were
carrying more vertical space than the one-to-four rows they introduce, and
the rows themselves had a lot of air between them. Both pulled in.

Delete stays on the collapsed row, where it is reachable without opening a
card, and it no longer toggles the card when clicked — inside a `<summary>`
that needed stopping explicitly, or the confirm dialog would appear over a
card that had just opened underneath it.

Nothing moved between sections and nothing was removed. This is layout
only.

---

## From build 2026-09-17-e

**The advisor on the page is the advisor that answers.** Opening a
participant link stored that link's advisor in the session, and it
overrode the page on every later request in the same browser — so
`/a/alan-friedman` rendered Alan while `/advisor/speak` looked up a
different advisor's voice sample and `/chat` answered from their knowledge
base. This was the cause of the "no voice sample has been uploaded"
message on an advisor who plainly had one.

**Voice samples show which advisor they belong to** (`-d`), with a "Wrong
advisor? Copy this recording to another" control. **Voice samples are no
longer destroyed on save** (`-c`) — the old path ran `DELETE` then
`INSERT`; it is an upsert now, with replacements archived and restorable.
**`/health` reports advisor voice state** (`-b`). **Preview Voice reports
which voice it used and why** (`-a`).

---

## From build 2026-09-16-j

**Admin panel.** Atlassian design language in J3P colours; sentence case
and larger type; contrast-checked status colour. One tab per request —
Overview 553 KB → 71 KB. Advisor detail in five bulk queries rather than
five per advisor. Per-advisor participant links with bulk CSV/XLSX upload
and export. Automatic learning toggle merged into Continuous Learning.
Copied links are https.

**Participant chat.** The "Error: Unknown error" bug. The cloned voice
timing out on long replies. The idle prompt interrupting typing. The
duplicate feedback box.

---

## Installing

Replace `app.py`, commit to `main`. Railway rebuilds on push. Check
`/health` reports `"version": "2026-09-17-f"`.

`admin-atlassian.css` and `admin-refresh.css` in the repo root are dead
files; the CSS is inlined in `ADMIN_HTML`. Safe to delete.
