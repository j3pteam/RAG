# J3P Advisor — build 2026-09-22-c

`app.py`, plus the pre-deploy checks (including `urlfor_check.py`).

---

## FLASK_SECRET_KEY, found during the product audit

If `FLASK_SECRET_KEY` is not set in the environment, the app falls back to
`os.urandom(24)` — **which runs separately in each worker**. Two workers,
two different session keys. A cookie signed by one is rejected by the other.

The effects look like flakiness rather than a missing setting:

- sign-in and the release acknowledgment drop at random
- the current conversation is lost between requests
- every redeploy signs everyone out
- anonymous transcripts are orphaned, because the history token changes

This build **says so plainly at startup** and shows a banner at the top of
Diagnostics when it applies.

**Worth checking on your deployment today**, independently of anything to do
with selling. Some of the session oddities earlier in this project would be
consistent with it — if the banner is showing, set `FLASK_SECRET_KEY` to a
fixed random value and several intermittent problems may simply stop.

---

## Installing

Replace `app.py`, keep the check scripts alongside. Diagnostics should
report `2026-09-22-c`.
