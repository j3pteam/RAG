# J3P Advisor — build 2026-09-21-j

`app.py`, plus the pre-deploy checks (including `urlfor_check.py`).

---

## Conversation history, internal advisor only

A rail down the left of `/a/j3p-internal`, listing past conversations
newest first. Each is titled with the first thing you said — a timestamp
alone tells you nothing about which one you are looking for.

Clicking one **loads it and continues it**, rather than showing a frozen
copy. Going back to a conversation usually means carrying on with it, and a
read-only view would mean copying text out to continue.

Open by default on wide screens, off-canvas behind a "Conversations" button
on narrow ones, and the choice is remembered.

## What had to change underneath

**"New conversation" was deleting the transcript.** There was no history to
list because the rows were being removed — nothing distinguished one
conversation from the next, so clearing was the only option.

`chat_history` now carries a `conversation_id`, added automatically on the
existing table. New conversation **rotates** that id instead of deleting, so
the previous conversation stays readable.

**Only on an internal advisor.** Everywhere else New Conversation still
deletes, exactly as before. A participant pressing that button is entitled
to expect their transcript gone, and quietly retaining it because a feature
elsewhere finds it useful would change what the button means. That is a
promise worth keeping even when no one would notice.

Existing rows have no conversation id and are treated as one earlier
conversation; nothing is lost.

## Access

Both endpoints check the server side, not just the sidebar:

| Caller | Result |
|---|---|
| Client-facing advisor | 403 |
| Internal advisor, not signed in as admin | 403 |
| Internal advisor, signed-in admin | allowed |
| No advisor (default persona) | 403 |

Hiding a sidebar does not stop anyone calling the endpoint behind it, and
these endpoints return whole transcripts. On client pages the script is
inert — the rail element does not exist, so no request is ever made.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-21-j`.

The first conversation you have after deploying starts the history; earlier
ones were already deleted by the old behavior and cannot be recovered.
