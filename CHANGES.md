# J3P Advisor — build 2026-09-20-f

`app.py`, plus the pre-deploy checks. Includes everything from `-e`.

---

## Tables render as tables

The Investment table in your screenshot arrived as a wall of pipe
characters:

```
| Phase | Scope | Fee | |---|---|---| | Phase A: Leadership Alignment, …
```

The markdown renderer handled headings, lists, bold, code and links — but
not tables. The advisor writes pricing, phasing and comparisons as tables,
so this is not an edge case; it is how a proposal looks.

Now rendered properly, with column alignment honoured (`---:` right-aligns
a fee column), bold and links working inside cells, and a gold rule under
the header to match the rest of the reply styling. Wide tables scroll
inside their own box so they never push the whole reply sideways on a
phone.

A line that merely contains pipes is left alone — a table is only a header
row followed by a `|---|---|` separator, so ordinary prose with a pipe in
it is not mangled.

Verified against a real proposal table: three header cells, three body
rows, right-aligned fee column, `**Total**` still bold inside its cell, no
raw pipes left, and the paragraph after the table still rendered.

---

## Still open: the sound not stopping

The tab in your screenshot still shows the speaker icon while the avatar
reads "Ready", which is the same mismatch as before — so I do not think
this is resolved yet.

`-e` added a last-resort stop that pauses every `<audio>` element on the
page. If that is now deployed and the sound still continues, the one thing
that would tell me where it is actually coming from is, with the reply
speaking, in the browser console:

```
window.__stopAllSpeech()
```

Stops → something is not calling it, which narrows it to the toggle wiring.
Continues → it is coming from a source I have not accounted for, and the
console will likely name it.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-f`.
