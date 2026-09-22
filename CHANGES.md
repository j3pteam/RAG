# J3P Advisor — build 2026-09-22-a

`app.py`, plus the pre-deploy checks (including `urlfor_check.py`).

---

## Deleting a conversation

A × appears on each row in the rail. **First click arms it and it changes to
"Delete?"; second click removes the conversation.** It disarms itself after
four seconds if you do not follow through.

Two clicks rather than one because this cannot be undone, and rather than a
browser `confirm()` because a modal for removing one row is heavier than the
action deserves. The second state says what it will do instead of just being
a second click.

Deleting the conversation currently on screen starts a fresh one rather than
leaving the page pointing at messages that no longer exist.

The delete is scoped in the SQL itself:

```sql
DELETE FROM chat_history WHERE token = %s AND conversation_id = %s
```

The token comes from the session, never the request. A conversation id from
someone else's history matches nothing rather than deleting their
transcript — the check cannot be forgotten because it is part of the
statement.

## The rail was covering the page

Your screenshot shows the banner reading "ON." and the greeting reading
"ello" — the rail was sitting on top of the content instead of moving it
across.

My fault: the rule shifted `.chat-shell`, an element that **does not exist**
on this page. The header, transcript and composer are ordinary flow children
of `body`, so the selector matched nothing and the margin was never applied.

The page now shifts as a whole (`body.hist-on { padding-left: 264px }`), and
explicitly does not shift on narrow screens, where the rail is an overlay
and moving the page under it would be wrong.

I should have caught that — I wrote a selector for a structure I had not
checked.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-22-a`.
