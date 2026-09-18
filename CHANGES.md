# J3P Advisor — build 2026-09-18-b

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## "Show full history" dropped you on Overview

Three controls in the conversation log were written when the active tab was
held in the browser, so the URL carried no tab at all:

```html
<a href="?filter=...&advisor=...&log_limit=all">Show full history</a>
<a href="?filter=...&advisor=...&log_limit=25">Show recent only</a>
<form method="GET" action="/admin">   <!-- the filter dropdowns -->
```

Once tabs moved to the server, a URL without `tab=` resolves to the default
— Overview. So asking for the full history, or changing the filter, landed
somewhere else entirely and silently discarded what had just been set. The
links were correct when written; the tab change in build `2026-09-16-b`
invalidated them and this was missed.

All three now carry `tab=activity`.

I swept the rest of the template for the same mistake: every other
query-string link and GET form includes a tab, and of the 91 server-side
redirects to the dashboard, the only three without one are the post-sign-in
redirects, where landing on Overview is correct.

---

## From build 2026-09-18-a

**The booking button names the advisor.** "Schedule time with Alan
Friedman" on his own pages; the default persona keeps the generic label,
since someone on the main link has not been matched with anyone yet.

## From build 2026-09-17-m

**Queries hoisted out of the render call and gated by tab.** Six database
calls sat in the argument list of `_cached_render` and were being timed as
"template render". Settings went from 15 queries to 3, Overview to 4.

## From earlier

Diagnostics tab (`-l`). Connection reuse, made fail-safe after it broke the
panel (`-i`, `-j`). Advisors collapsing to one card at a time (`-f`). The
advisor on the page being the advisor that answers, plus the voice-sample
archive and slug work (`-e` through `-a`).

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-18-b`.
