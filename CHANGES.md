# J3P Advisor — build 2026-09-18-c

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## The booking button is a setting, not two URLs

Each advisor had two near-identical links — `/a/<slug>/scheduling` and
`/a/<slug>/no-scheduling` — that differed only in whether the booking button
appeared. That meant choosing the behaviour at the moment of copying, and
never being able to see or change what a link already sent out was doing.

Both sections are replaced by a control.

**Per advisor.** "Scheduling Links" is now **Booking button**, with three
choices: follow the site setting, always show, always hide. The default
persona gets a straight on/off switch for the main link.

**Per participant link.** The links table has a new Booking column: *Follow
advisor*, *Show*, *Hide*, changeable in place from the dropdown. Follow
advisor is the default, and stays the default for links created later —
the setting is stored as "no preference" rather than copying the advisor's
current value, so a link does not silently diverge when the advisor's
setting changes.

The override exists for the participant who should not be sold a session —
someone mid-engagement, or a courtesy link.

### Old links keep working

`/scheduling` and `/no-scheduling` still resolve. Links already in
circulation must not break, and a URL that says explicitly what it wants
still wins over the toggles. They are simply no longer offered in the admin
panel.

Precedence, verified:

| Situation | Button | Decided by |
|---|---|---|
| Advisor set to always hide | hidden | the advisor |
| Advisor set to follow site | shown | the site setting |
| Link set to Hide, advisor shows | hidden | this participant's link |
| Link follows advisor, advisor hides | hidden | the advisor |
| An existing `/no-scheduling` link | hidden | the URL |
| An existing `/scheduling` link | shown | the URL |

The new column is added to `participant_links` on first use — no migration
step.

---

## From build 2026-09-18-b

Conversation log filters and the "Show full history" link were dropping back
to Overview: they were written before tabs moved server-side and carried no
`tab=`.

## From build 2026-09-18-a

The booking button names the advisor whose session it is.

## From earlier

Queries hoisted out of the render call and gated by tab — Settings went from
15 queries to 3 (`-m`). Diagnostics tab (`-l`). Connection reuse made
fail-safe (`-i`, `-j`). Advisors collapsing to one card at a time (`-f`).
The advisor on the page being the advisor that answers, plus the
voice-sample archive and slug work (`-e` through `-a`).

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-18-c`.

Worth checking after deploying: open an advisor, set Booking button to
"Always hide", and confirm their session link no longer shows it — then set
one participant link to "Show" and confirm that person does.
