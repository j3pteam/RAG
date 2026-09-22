# J3P Advisor — build 2026-09-21-d

`app.py`, plus the pre-deploy checks (including `urlfor_check.py`).

---

## Internal is now genuinely first on the page

Last build put it above the other advisors but still below the Default
persona's card. It now comes before that too — first thing under the tab,
which is where someone looks.

That needed the default persona's card to become a Jinja macro so it could
be emitted at the right point in the ordering rather than being fixed where
it happened to sit in the file. No markup was duplicated.

Verified in three configurations:

| Advisors present | Order rendered |
|---|---|
| internal + 2 client | internal → default → client → client |
| internal only | internal → default |
| no internal | default → client |

The default card appears exactly once in each — including the case with no
client-facing advisors, where the boundary that triggers it never arrives.

## One link, and nothing else

The internal card's Links section is now a single row:

```
Link to the advisor
  https://…/a/j3p-internal   [Copy]
```

with a line explaining that it opens the ordinary session interface, only
signed-in admin accounts can load it, and it is safe to bookmark but not to
paste anywhere a client could see.

Gone from that card: **Booking button** and **Participant Links**.

The participant-links form was worse than redundant — creation is refused
server-side for internal advisors, so the form could only ever fail. That is
what produced the bare "Please fill out this field" in your screenshot: a
form that cannot succeed, giving no reason.

Client-facing cards are unchanged — booking button, participant links and
knowledge portal all still there. Confirmed card by card in the render test.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-21-d`.
