# J3P Advisor — build 2026-09-19-f

`app.py`, plus the pre-deploy checks.

**Includes the Activity 500 fix from `-d`.**

---

## The conversation log collapses too

`-e` collapsed three of the four Activity sections and left the log — the
longest one — permanently open, which rather defeated the point. All four
now behave the same:

```
▾ Ratings                  36 rated · 86% helpful
▸ Continuous Learning      on — every 24h, last run Sep 18
▸ Briefings — Main Link    1 waiting
▸ Conversation Log         25 records
```

The summary reflects what you are actually looking at — it reads
"25 records (full history)" after clicking Show full history, and names the
advisor when the log is filtered to one.

**The filter and export controls moved below the header.** They sat in the
same row as the title, and a `<summary>` swallows clicks on anything inside
it — so picking an advisor from the dropdown would have collapsed the
section instead. They are in the section body now, right-aligned above the
table.

Ratings stays open by default. The rest start closed.

---

## Verification

```
$ ./check.sh
1/4  syntax                            ok
2/4  undefined names                   ok
3/4  module-level definition order     ok
4/4  rendered HTML is well-formed      ok
```

All eight tabs render with balanced tags, and the four Activity sections
were confirmed by inspecting the rendered markup rather than by eye.

---

## From -e

Activity sections made collapsible, and a stray duplicate `</label>` in the
Settings tab removed — a pre-existing fault the new HTML check found on its
first run.

## From -d

The Activity 500 (`personality_summary`, `personality_tips` and `locations`
referenced as variables when they were only ever inline arguments), an
`UnboundLocalError` in the advisor-scoping code, and a pre-existing
oversized-upload 500.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-19-f`.
