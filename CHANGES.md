# J3P Advisor — build 2026-09-21-a

`app.py`, plus the pre-deploy checks. Includes everything from `-o`.

---

## The internal advisor section is now where you would look for it

I put it in a poor place. It sat below the Default persona card, most of a
page down — for a one-time setup action someone goes looking for
deliberately, which belongs near the top.

It now appears directly under the **Advisor Profiles** intro, above
"Export or import advisors":

```
Advisor Profiles
  Internal J3P advisor          <- here
  Export or import advisors
  Add or update an advisor
  [advisor cards]
```

It only shows when no internal advisor exists yet, and only to accounts that
can edit advisors. Once you create one, the section disappears and the
advisor's own card carries the internal badge and the switch.

## If it still is not there

Check **Diagnostics → Build → Version** reads `2026-09-21-a`. The section
was added in `-o`, so anything earlier will not have it at all.

---

## Installing

Replace `app.py`, commit to `main`.
