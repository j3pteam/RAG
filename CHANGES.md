# J3P Advisor — build 2026-09-21-b

`app.py`, plus the pre-deploy checks — **including a new one,
`urlfor_check.py`.** Copy that across too.

---

## The 500

My bug, and a plain one. The route redirected with:

```python
url_for("admin", tab="advisors")
```

The admin view function is called `admin_dashboard`. There is no endpoint
named `admin`, so Flask raised before anything else ran — the moment the
button was clicked.

**Eight call sites were wrong, and only four of them were mine.** The other
four were in the existing "Make internal / Make client-facing again" switch,
which means that switch would have produced the same 500 whenever it was
next used. It had been sitting there. All eight now point at
`admin_dashboard`.

## Why nothing caught it, and what now will

None of the four pre-deploy checks could see this:

- the syntax is valid
- the endpoint is a **string**, not an identifier, so pyflakes sees nothing
  to resolve
- definition order is irrelevant
- the render test renders templates; it never follows a redirect

So it could only fail at the moment someone clicked — the worst time to find
out, and exactly what happened to you.

**`urlfor_check.py` is now step 5 of `check.sh`.** It parses every
`@app.route` to collect the real endpoint names, then checks every
`url_for("…")` in the file — Python call sites and the ones inside the Jinja
templates — against that list.

```
5/5  url_for targets resolve
     ok  (124 routes, every url_for resolves)
```

Confirmed against the actual bug: reintroducing the bad call makes the check
fail and name the line.

This is the fifth check, and like the other four it exists because something
shipped broken without it.

---

## Installing

Replace `app.py` **and add `urlfor_check.py`** alongside the other check
scripts. Commit to `main`. Diagnostics should report `2026-09-21-b`.

Then the button should work: Advisors → Internal J3P advisor → Create.
