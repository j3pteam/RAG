# J3P Advisor — build 2026-09-24-e

`app.py`, the pre-deploy checks, `verify_brand.py`, `brands/`, and the
deployment guides.

---

## Client engagements live only on Add Client

They no longer appear in the Advisors list. One place to look, one place to
forget.

| | Advisors tab | Add Client tab |
|---|---|---|
| Alan Friedman | yes | no |
| A client engagement | **no** | yes |

## What had to move with them

Removing them from Advisors would have removed the only way to issue their
participant links — the links are what you actually send to a client's team,
so that would have made the engagement useless rather than tidier.

Both now sit inside each engagement on the Add Client tab:

- **Participant links** — one per person on their team, as before
- **Photo** — and saving it returns you to Add Client rather than dropping
  you on the Advisors tab

The existing redirect helper already anticipated a second entry point and
whitelisted the tabs it would accept; `clients` is now one of them, which
was the one-line change its comment predicted.

## Two bugs found while testing this

**The Add Client tab would have thrown a 500.** `participant_links_section`
is a Jinja macro, and Jinja resolves macros in source order — it was defined
inside the Advisors tab, which renders *after* Clients. Using it there
raised `'participant_links_section' is undefined`. Moved above its first
use.

**A form posted to a route that does not exist.** I wrote
`/admin/advisor-photo/<slug>` from memory; the real route is
`/admin/advisors`. It would have 404'd on save. The `url_for` check cannot
catch this one — the action is a literal string, not a `url_for` call — so
it took rendering the page and reading the form to find.

One thing deliberately left: every advisor still appears in the participant
link **destination dropdown** on the default persona's card. That is a
chooser for where a link should point, not the engagement being managed, and
removing entries would only make links harder to issue.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-e`.
