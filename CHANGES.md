# J3P Advisor — build 2026-09-19-b

Two files: `app.py` (replaces the existing one) and `import_order_check.py`
(new, optional — see below).

---

## Why the deploy kept failing

Not the healthcheck being slow. The worker was never starting.

In build `-g` I added the literature-search ingest route and placed it at
line 8103:

```python
@app.route("/admin/research/ingest", methods=["POST"])
@require_permission("edit_knowledge")        # defined at line 8417
def admin_ingest_research():
```

Decorators are evaluated when the module is imported, so Python hit
`require_permission` 300 lines before it exists and raised `NameError`. The
module never finished importing, gunicorn's worker died, and nothing was
listening when Railway probed `/health` — which presents as "Healthcheck
failure" and looks identical to a slow response.

The route is now beside the other admin routes, all of which are defined
well after `require_permission`.

**The `-a` healthcheck fix was still correct** and is included. `/health`
touching the database was a real fault; it just was not this one. Both are
fixed.

## Why I did not catch it

Every build this week was verified with `ast.parse`, which checks syntax
and nothing else. A name used 300 lines before it is defined is
syntactically perfect. The check I was running could not have found this.

`import_order_check.py` closes that gap. It walks the module top to bottom,
tracks what has been defined, and reports any name used at module level —
in a decorator, a default argument, a module-level assignment — before it
exists.

```
$ python3 import_order_check.py app.py
app.py: every module-level name is defined before it is used
```

Verified two ways: it reports clean on this build, and on a minimal file
reproducing the bug it flags exactly the name Python's own `NameError`
names. Run it before any deploy; it takes under a second and needs no
dependencies.

You do not have to commit it — it is a development tool, not part of the
app. But committing it means it is there next time.

---

## Everything else is unchanged from -g

PubMed and OpenAlex literature search. Session transcripts scopeable to
assigned advisors. Participant text kept out of the deploy logs. Replies
checked back against the knowledge base after generation.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-19-b`.
