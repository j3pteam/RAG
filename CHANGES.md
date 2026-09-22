# J3P Advisor — build 2026-09-22-e

`app.py`, the pre-deploy checks, and `DEPLOYING_A_CLIENT.md`.

---

## A client conversation was in the internal history

My bug, and the more serious of the two things in your screenshot.

`chat_history` rows are keyed by the history token, and that token is
derived from **your email** — so it is identical across every advisor you
use while signed in. Nothing recorded which advisor a conversation happened
with. The internal rail listed conversations by token alone, so it listed
everything you had ever said to any advisor.

Rows now carry `advisor_slug`, and listing, opening and deleting are all
filtered by it:

| | Before | After |
|---|---|---|
| Internal rail | your client threads **and** internal ones | internal only |
| Default advisor | same mixed list | its own only |

Your earlier conversations have no advisor recorded, so they will not appear
in the internal rail — which is the correct outcome, since they were not
internal conversations.

The same filter is on the delete, so a conversation can only be deleted from
the advisor it belongs to.

## "I cannot access the message"

Clicking a conversation that could not be opened did nothing at all, which
is indistinguishable from a click that missed. The rail now says why —
"That conversation is no longer available" for a 404, "Could not open that
conversation" otherwise.

I cannot tell from here which of those you were hitting. If it persists on
this build, the message will name the failure and I can fix the actual
cause rather than the next guess.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-22-e`.
