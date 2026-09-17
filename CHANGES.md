# J3P Advisor — build 2026-09-17-e

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## The voice bug: the page said one advisor, the server used another

Working in incognito but not in a normal browser was the tell. Incognito has
no session; the normal browser had one.

Opening a participant link (`/p/<token>`) stored that link's advisor in the
session, and that stored advisor **overrode the page** on every later
request in the same browser. Visit `/a/alan-friedman` afterwards and the
page renders Alan — name, photo, greeting — while `/advisor/speak` looks up
the *linked* advisor's voice sample. That advisor has none, so it reported
"no voice sample has been uploaded for them yet" about an advisor who
plainly had one in the admin panel.

Nothing on screen disagreed with itself, which is why this took so long to
find. The sample was never deleted and was never on the wrong slug.

**The same precedence applied to `/chat`**, so replies were being generated
as the linked advisor — their knowledge base, their expertise, their
coaching style — while the page showed Alan. That is the more serious half
of this bug, and it is fixed by the same change.

### What changed

The advisor the page rendered is now the advisor that answers. The page
sends its slug with every request; that wins.

The link's own pages are unaffected: `/p/<token>` renders with the link's
advisor, so the slug it sends already *is* the linked advisor. The only
case that changes is the one where the two genuinely differ — someone
navigating to a different advisor on purpose. Identity and conversation
history still follow the participant link; only "who answers" moves.

Verified across six scenarios, including a participant on their own link, a
cached page that sends no slug, and a page naming an advisor that has since
been deleted.

### Clearing it on your own browser

The fix applies from the next request — no need to clear anything. If you
want to be certain you are seeing current behaviour, click NEW CONVERSATION
or use a private window.

---

## Also in this build

**Voice samples show which advisor they belong to** (2026-09-17-d). Each
Voice Sample section states its slug, and where a sample exists there is a
"Wrong advisor? Copy this recording to another" control. The default
persona and a named advisor can share a display name, which made their two
sections indistinguishable.

**Voice samples are no longer destroyed on save** (2026-09-17-c). The save
path ran `DELETE` then `INSERT`, so the recording existed only in memory in
between. It is an upsert now. Replacements and removals are archived, last
five per advisor, restorable from a "Previous recordings" panel.

**`/health` reports advisor voice state** (2026-09-17-b).

**Preview Voice reports which voice it used and why** (2026-09-17-a).

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
`/health` reports `"version": "2026-09-17-e"`.

`admin-atlassian.css` and `admin-refresh.css` in the repo root are dead
files; the CSS is inlined in `ADMIN_HTML`. Safe to delete.
