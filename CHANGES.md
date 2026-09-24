# J3P Advisor — build 2026-09-24-k

`app.py`, the pre-deploy checks, and `patch_exports.py` (unchanged).

---

## The link was created. The page could not show it.

My bug. The admin panel loads data per tab, to avoid running every query on
every page:

```python
want_advisors = active_tab == "advisors"
_participant_links = list_participant_links() if want_advisors else []
```

When I moved client engagements onto their own tab, I moved the sections but
not the data behind them. On Add Client, `want_advisors` is false — so the
participant-links list was **always empty**, whatever you created.

"No participant links for Roy Friedman yet" was not a failure report. It was
the page truthfully describing a list it had been handed empty.

The same applied to **Their documents**: the document-to-advisor map was
loaded only for the Knowledge and Advisors tabs, so that section would have
stayed empty no matter what you uploaded.

Both now load for Add Client as well. Verified by rendering the tab with a
link present — it lists, and the "none yet" line is gone.

## Worth checking on your deployment

The link you made for "Alan" was almost certainly created. Open Add Client
after deploying and it should be listed under Roy Friedman. If you made
several while nothing appeared, they will all be there — nothing was lost,
it simply was not shown.

## A pattern in these last few builds

Three faults in a row have come from the same thing: moving a feature to a
new tab and leaving something behind — the instructions, the redirect
targets, and now the data. Each time the visible symptom pointed somewhere
else. A move is not one change, and I have been treating it as one.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-k`.
