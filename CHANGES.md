# J3P Advisor — build 2026-09-18-a

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## The booking button names the advisor

On an advisor's own page the button said "Schedule time with a J3P Advisor"
— underneath that advisor's photo, their name in the header, and a greeting
naming them. It already pointed at their own calendar when they had one, so
the link was right and only the label was generic.

| Page | Button now reads |
|---|---|
| `/a/alan-friedman` | Schedule time with Alan Friedman |
| `/p/<token>` assigned to Alan | Schedule time with Alan Friedman |
| `/a/bruce-gewertz` | Schedule time with Bruce Gewertz, MD |
| `/` and `/scheduling` (default persona) | Schedule Time With a J3P Advisor |

The default persona deliberately keeps the generic label. Someone on the
main link has not been matched with anyone yet, so naming a person there
would be wrong.

Two details worth recording:

**Built from the name, not substituted into the stock label.** The
configured label carries an article — "with **a** J3P Advisor" — which does
not survive swapping in a person's name. The same problem already existed
in the greeting, where "with the J3P Advisor" had to lose its article to
become "with Alan Friedman", and it is handled the same way here.

**Scoped to named advisors only.** My first attempt put this inside the
function that renames the persona, which also runs for the default persona
when it has a display name — that would have produced "Schedule time with
J3P" rather than "J3P Advisor" on the main link.

The footer sentence that introduces the button follows the same rule.

---

## From build 2026-09-17-m

**Queries hoisted out of the render call and gated by tab.** Six database
calls were sitting in the argument list of `_cached_render`, so they were
timed as "template render" — 841 ms that was not rendering. Hoisting them
showed most were not needed on most tabs: Settings went from 15 queries to
3, Overview to 4, Advisors to 8.

## From earlier

Diagnostics tab (`-l`). Connection reuse, made fail-safe after it broke the
panel (`-i`, `-j`). Advisors collapsing to one card at a time (`-f`). The
advisor on the page being the advisor that answers, plus the voice-sample
archive and slug work (`-e` through `-a`).

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-18-a`.
