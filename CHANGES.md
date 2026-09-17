# J3P Advisor — build 2026-09-17-g

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## Two fixes

**The chevron is on the row edge.** It was dropping below the status chips
and sitting under the photo. `.advisor-head` is a wrapping flex container
and the chips take a full row, so a flex-positioned marker followed them
down. It is positioned rather than laid out now, pinned to the right of the
row regardless of how many chips an advisor has, and it darkens on hover.

**The render time is on the page**, beside the build number:

```
Admin   build 2026-09-17-g · 180 ms
```

After a deploy or a scale-down the first load also shows what the cold
start cost:

```
Admin   build 2026-09-17-g · 420 ms, cold start 6.8s
```

---

## Why that number matters for the slowness

It has been measured since the first report — logged as `[timing]` on every
admin request, and written into an HTML comment at the foot of the page —
and neither form survives a screenshot, which is how the reports arrive. So
four rounds of work on this have been informed guesses.

The number distinguishes two completely different problems:

- **A high figure (over ~800 ms)** means the server. The `[timing]` log line
  breaks it into phases, and I can act on that directly.
- **A low figure (under ~300 ms) with a page that still feels slow** means
  the server finished quickly and the time is going somewhere else: the
  browser rendering, the network, or a cold container. That would redirect
  the work entirely — nothing further in the query layer would help.

**Cold start is the one I would bet on now.** Railway containers scale down
when idle, and the first request afterwards pays for importing psycopg,
voyageai, trafilatura, tokenizers and numpy, plus the schema check, before
it answers. That is several seconds, it only happens on the first load, and
it looks exactly like "the admin panel is very slow" — while the second
load is fast and the logs look healthy. The cold-start figure now appears
on that first page, which confirms or rules it out in one glance.

So: open the admin panel and read the line under "Admin". Send me that.

---

## From build 2026-09-17-f

**Advisors page: one card open at a time.** Each advisor is a collapsed
row — photo, name, slug, status chips — and opening one closes the others.
"Add or update an advisor" collapses too. Tighter spacing on the group
captions and section rows.

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
Overview 553 KB → 71 KB. Advisor detail in five bulk queries rather than
five per advisor. Per-advisor participant links with bulk CSV/XLSX upload
and export. Copied links are https.

**Participant chat.** The "Error: Unknown error" bug. The cloned voice
timing out on long replies. The idle prompt interrupting typing. The
duplicate feedback box.

---

## Installing

Replace `app.py`, commit to `main`. Railway rebuilds on push. Check
`/health` reports `"version": "2026-09-17-g"`.

`admin-atlassian.css` and `admin-refresh.css` in the repo root are dead
files; the CSS is inlined in `ADMIN_HTML`. Safe to delete.
