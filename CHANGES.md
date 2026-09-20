# J3P Advisor — build 2026-09-20-k

`app.py`, plus the pre-deploy checks. Includes everything from `-j`.

---

## The speaker button and the avatar both stop the voice

**While something is speaking, the Speak button means stop.** It was a
setting toggle — so pressing it to silence a reply could switch auto-speak
*on* and start reading the next one, the opposite of the gesture. If
auto-speak was on, one press now both stops the reply and turns it off,
rather than needing a second press to stop the next one starting.

**Clicking the advisor's photo stops them too**, whichever reply is playing.

Both work during the couple of seconds between the click and the first
sound, while the audio is still being fetched. Nothing is audible then, but
a click plainly means stop — and previously it was ignored.

| | Idle | Speaking | Audio still loading |
|---|---|---|---|
| Speaker button | toggles auto-speak | stops | stops |
| Avatar | reads the last reply | stops | stops |

## The label you asked about

`(their own voice)` was removed in `-g`, along with the `(32 parts)` count
on the note. Both are in this build. Your screenshot still shows them, which
means the running version is older than `-g` — so none of the last five
builds are live yet, including the New-conversation stop and the
speaks-over-itself fix.

---

## Installing

Replace `app.py`, commit to `main`.

**Then check `/health` and confirm it reports `2026-09-20-k`.** Six of my
last seven fixes have been tested against a build that did not contain them,
which has cost us both time. If the version does not change after a push,
the deploy is not completing and that is worth solving before anything else.
