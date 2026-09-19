# J3P Advisor — build 2026-09-19-c

Two files: `app.py` and `import_order_check.py` (the pre-deploy check from
`-b`; unchanged, included so you have it).

**This includes the `-b` import fix.** If `-b` has not deployed yet, deploy
this instead.

---

## Conversation log, cleaned up

**Locations were setting the height of every row.** "New York, New York,
United States" in a 130-pixel column wraps to five lines, and a table row is
as tall as its tallest cell — so every row was five lines high while the two
columns anyone actually reads, the question and the reply, sat truncated in
a corner of it.

Locations are now written the way a person would write them, on one line:

| Stored | Shown |
|---|---|
| New York, New York, United States | New York, NY |
| Princeton, New Jersey, United States | Princeton, NJ |
| San Francisco, California, United States | San Francisco, CA |
| London, England, United Kingdom | London, England |
| Toronto, Ontario, Canada | Toronto, Ontario |

US states abbreviate, the country drops when it is the common one, and the
full value is still on hover. Non-US locations keep their region, since
abbreviating those would be guesswork.

**Empty columns are gone.** Personality and How-to-interact only have
content when a participant has taken the assessment, which most have not —
so they were two columns of "—" taking width from the ones that matter.
They appear when at least one visible row has something in them, and
otherwise they are not rendered at all. Same for Location.

**Question and reply get the space back** — 26% of the table each, up from
a fixed 280px while Location took 130px to say "New York" badly.

---

## Also in this build

**The import fix from `-b`.** The literature-search route was decorated
with `@require_permission` 300 lines before that function is defined, so
the module raised `NameError` on import and no gunicorn worker ever
started. That presented as a healthcheck failure. The route now sits with
the other admin routes.

**`/health` touches nothing** (`-a`) — no database call on the path Railway
probes on a cold container.

Run `python3 import_order_check.py app.py` before deploying; it catches the
class of error that caused the last two failed deploys and takes under a
second.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-19-c`.
