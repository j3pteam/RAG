# J3P Advisor — build 2026-09-24-g

`app.py`, the pre-deploy checks, `verify_brand.py`, `brands/`, and the
deployment guides.

---

## Why clicking that conversation did nothing

My bug, and a careless one. `openConversation` began with:

```js
if (btn.classList.contains("current")) return;
```

I wrote that to avoid reloading a conversation that was already open. But
**"current" means the session is pointing at it, not that it is on screen** —
the page renders only the greeting on load. So the one case where someone
most obviously wants to click is the one case I made do nothing, silently.

The early return is gone. Clicking any conversation loads it.

## And the transcript comes back on its own

Reopening the page now restores the conversation you were in, rather than
showing a greeting while the model still has the full history — the page and
the advisor were disagreeing about what had been said.

It only runs when the transcript is genuinely empty, so it never overwrites
a conversation in progress.

## The earlier disappearance, and why it will stop

Your previous screenshot showed no conversations at all. That was a
different fault, and worth knowing about because it affects more than this
rail.

A signed-in person's history token was derived from **`app.secret_key` plus
their email**. With `FLASK_SECRET_KEY` unset, each worker generates its own
key at startup — so the same person got a different token on every worker
and after every restart:

```
worker 1          u_7f17b295d1c4b968…
worker 2          u_6e70eb33153f9cb4…
after a redeploy  u_45f42c4b0a4469a4…
```

The conversations were being recorded. They were being recorded under an
identity that no longer existed.

Two things were wrong: the key may be unset, and a session key should never
have been the salt in the first place — it is meant to be rotatable, and
tying identity to it means rotating it silently destroys every transcript
ever recorded.

Now: `FLASK_SECRET_KEY` is used when set, so a properly configured
deployment keeps the tokens it already has. Otherwise a salt is generated
once and **persisted**, stable from then on. If it cannot be persisted the
log says so plainly rather than appearing to have fixed it.

**Still worth setting `FLASK_SECRET_KEY`.** It fixes sign-ins and the
release acknowledgment dropping at random, which this does not touch.

Conversations recorded under an old, vanished token cannot be recovered —
there is no way to know which token belonged to whom.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-g`.
