# J3P Advisor — build 2026-09-17-h

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## Where the four seconds go

The Advisors tab reported **3928 ms, cold start 1.4s**. That settles two
things: it is not the container waking up, and it is not the browser. The
server takes four seconds.

What it does not yet say is *which part*. The phase marks were too coarse —
one of them covered four separate queries. This build splits them so each
significant call is timed on its own, and makes a slow page show its own
breakdown:

```
Admin   build 2026-09-17-h · 3928 ms, cold start 1.4s
        voice archive map        2600 ms
        template render           480 ms
        list_documents            120 ms
        list_advisors              95 ms
```

The four slowest phases appear under the build line whenever a page takes
over a second. Below that they stay hidden — under a second is noise.

Newly timed separately: `list_documents`, `document_advisor_map`,
`list_advisors`, participant links, and each of the six per-advisor bulk
reads (personality, behavioural, 360, voice meta, voice archive, briefings)
rather than one lump.

**My guess, to be clear that it is one:** the voice archive map is the
newest query and the only one reading a table with audio in it. It selects
metadata only, so it should be cheap — but if Postgres is fetching the
BYTEA column to satisfy the row scan, that table holds several megabytes of
audio per row. The next screenshot will confirm or kill that in one glance,
and if it is something else the breakdown names it instead.

Load the Advisors tab and send me the four lines.

---

## From build 2026-09-17-g

Chevron pinned to the trailing edge of each advisor row — it had been
dropping below the status chips. Render time shown beside the build number.

---

## From build 2026-09-17-f

Advisors page collapses to one card at a time: photo, name, slug and status
chips per row, opening one closes the others. "Add or update an advisor"
collapses too.

---

## From build 2026-09-17-e

**The advisor on the page is the advisor that answers.** A stored
participant link was overriding the page, so `/a/alan-friedman` rendered
Alan while the voice and the replies came from a different advisor.

Plus: voice samples show their slug and can be copied between advisors
(`-d`); voice samples are no longer destroyed on save, and are archived and
restorable (`-c`); `/health` reports advisor voice state (`-b`); Preview
Voice reports which voice it used and why (`-a`).

---

## From build 2026-09-16-j

**Admin panel.** Atlassian design language in J3P colours; sentence case
and larger type; contrast-checked status colour. One tab per request —
Overview 553 KB → 71 KB. Advisor detail in bulk queries rather than per
advisor. Per-advisor participant links with bulk CSV/XLSX upload and
export. Copied links are https.

**Participant chat.** The "Error: Unknown error" bug. The cloned voice
timing out on long replies. The idle prompt interrupting typing. The
duplicate feedback box.

---

## Installing

Replace `app.py`, commit to `main`. Railway rebuilds on push. Check
`/health` reports `"version": "2026-09-17-h"`.

`admin-atlassian.css` and `admin-refresh.css` in the repo root are dead
files; the CSS is inlined in `ADMIN_HTML`. Safe to delete.
