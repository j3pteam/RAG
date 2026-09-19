# J3P Advisor — build 2026-09-19-e

`app.py`, plus the pre-deploy checks (`check.sh` and its three helpers).

**Includes the Activity 500 fix from `-d`.** Deploy this.

---

## Activity collapses into four sections

The tab was four unrelated things stacked vertically — ratings, the
learning engine, briefings, and a 25-row conversation log — so reaching any
one of them meant scrolling past the others.

Each is now a section that opens on click, with its headline figure in the
header so a closed section still answers the question you opened it to ask:

```
▸ Ratings                  36 rated · 86% helpful
▸ Continuous Learning      on — every 24h, last run Sep 18
▸ Briefings — Main Link    1 waiting
▸ Conversation Log         25 records
```

Ratings stays open by default — four numbers, no scrolling cost, and it is
the thing people glance at. The rest start closed. The chevron, hover
behaviour and spacing match the advisor cards, so the two tabs now behave
the same way.

## A stray tag, found by a new check

While verifying the markup I added an HTML well-formedness check across all
eight tabs. It immediately found a pre-existing fault in **Settings**: the
Participant Access form closes its `<label>` twice, a leftover from an
earlier edit. Browsers silently absorb that, which is why it survived every
visual review. Removed.

---

## The pre-deploy checks now run four things

```
$ ./check.sh
1/4  syntax                            ok
2/4  undefined names                   ok
3/4  module-level definition order     ok
4/4  rendered HTML is well-formed      ok
```

Each exists because something shipped broken without it:

| Check | Caught |
|---|---|
| `ast.parse` | syntax only — caught none of this week's failures |
| pyflakes | the Activity 500, the `UnboundLocalError` in advisor scoping, an oversized-upload 500 that predates me |
| `import_order_check.py` | the decorator that stopped every gunicorn worker booting |
| `tagcheck.py` | the duplicate `</label>` in Settings |

Needs `pip install pyflakes` once. Takes about two seconds. Run it before
every deploy — I am.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-19-e`.

`check.sh`, `import_order_check.py`, `tagcheck.py` and `render_test.py` are
development tools rather than part of the app. Committing them is optional,
but it is how the checks are there next time.
