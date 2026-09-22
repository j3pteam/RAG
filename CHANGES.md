# J3P Advisor — build 2026-09-22-f

`app.py`, the pre-deploy checks, and `DEPLOYING_A_CLIENT.md`.

---

## A conversation was following you between advisors

My bug, and it explains both of the last two reports.

`conversation_id` was stored per **session**, and a session spans every
advisor you visit. `load_history()` filtered by that id but not by advisor.
So moving from one advisor to another carried the conversation across: the
next advisor loaded the previous one's messages as its own context and
answered against them.

That is why the internal advisor appeared to hold on to the last
conversation — it genuinely had it in context. It is also why a client email
thread you had pasted elsewhere was sitting in an internal session.

Two changes:

- **The conversation id rotates when the advisor changes.** A conversation
  belongs to one advisor, and the id is now paired with the advisor it was
  started under.
- **History loading is filtered by advisor** as well as by conversation, so
  even a stale id cannot reach across.

Verified: two messages to two advisors in one session now sit in separate
conversations, and the internal advisor's context contains only what was
said to it.

## Why this kept surfacing as something else

Each time, the visible symptom pointed somewhere other than the cause — a
history list showing the wrong rows, then an advisor answering the wrong
question. The shared root was that a conversation had no owner. It has one
now.

Worth knowing: the pasted email was in that session's context, so it was
sent to the model as part of the conversation. That is a reason to run
**New Conversation** after pasting anything personal or client-confidential,
until deletion-on-request exists.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-22-f`.
