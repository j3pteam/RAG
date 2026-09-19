# J3P Advisor — build 2026-09-19-d

Files: `app.py`, plus `check.sh` and `import_order_check.py` (development
tools — see below).

---

## The 500 on Activity

My fault, from `-c`. The column flags I added referenced
`personality_summary`, `personality_tips` and `locations` as if they were
variables. They are not — they are built inline in the argument list of the
render call, so no name for them exists anywhere in the route. Referencing
them raised `NameError` on every load of the Activity tab.

They are now real locals, built before the render call. That also fixes a
second thing: `locations_for()` and `acknowledgements_for()` are two
database calls that were being made inside the argument list, so they were
counted as "template render" — the same mis-attribution fixed for other
arguments in `-m` and missed for these.

## Two more found in the same sweep

**`_advisor_rows` used before assignment.** The transcript-scoping code
from `-f` reads the advisor list at line 19307; the list was not loaded
until line 19351. Any account restricted to specific advisors would have
hit `UnboundLocalError` on the Activity tab. Owners were unaffected, which
is why it was not visible — the scope branch does not run for them. The
list is now loaded before the check that uses it.

**An oversized upload returned a 500 instead of an explanation.** This one
is not mine — it predates my involvement. In the chat upload handler, the
too-large error message references `filename`, which does not exist in that
scope:

```python
"error": f"{filename} is too large ({len(file_bytes)/1048576:.0f} MB)."
```

So a participant attaching a file over the limit got "Internal Server
Error" rather than being told the file was too big. It now names the file
properly.

---

## Why my checks kept missing these

`ast.parse` validates syntax and nothing else. Every one of these bugs is
syntactically perfect.

`check.sh` runs three things:

```
$ ./check.sh
1/3  syntax                            ok
2/3  undefined names                   ok
3/3  module-level definition order     ok
```

- **pyflakes** catches undefined names anywhere, including inside
  functions. It would have caught today's 500, the `UnboundLocalError`, and
  the pre-existing upload bug.
- **import_order_check.py** catches names used at module level before they
  are defined — the decorator that stopped every worker booting.

Needs `pip install pyflakes` once. Run `./check.sh` before each deploy; it
takes about a second. I am running all three on every build from here.

---

## Also in this build

Conversation log cleaned up (`-c`): one-line locations — "New York, NY"
rather than five wrapped lines — empty Personality and How-to-interact
columns dropped, and the question and reply columns given the space back.

The import fix (`-b`) and the healthcheck fix (`-a`).

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-19-d`.

`check.sh` and `import_order_check.py` are development tools, not part of
the app. Committing them is optional but means they are there next time.
