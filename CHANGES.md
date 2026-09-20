# J3P Advisor — build 2026-09-20-c

`app.py`, plus the pre-deploy checks.

---

## First, a likely explanation for the screenshot

That screenshot was taken a minute after the previous one, and `-b` was not
packaged until after it — so it was almost certainly still the old build.
Deploying `-b` alone may well have fixed it.

But raising a timeout was treating the symptom, and I should say so: a long
enough reply will exceed any fixed limit. Whatever number I pick, there is a
reply that beats it.

## The actual fix: synthesise in parts

A 4,000-character reply was one enormous synthesis request. The participant
waited for the **whole** thing before hearing a sound, and if it ran long,
the entire attempt was lost.

The reply is now split on sentence ends into pieces of at most ~700
characters. Each is a short request that comes back in a second or two:

| Reply | Parts | Longest part |
|---|---|---|
| 80 chars | 1 | 80 |
| 700 chars | 1 | 700 |
| 1,500 chars | 3 | 634 |
| 4,000 chars | 7 | 634 |

**Playback starts after the first part**, not after the last — so a long
reply begins speaking in about the same time a short one does. The next part
is fetched while the current one plays, so the joins are seamless. The
browser's own speech engine already worked this way, for exactly this
reason.

Three behaviours worth knowing:

- **Only the first part decides** whether the cloned voice is usable. If it
  works, playback has started before a later part could fail.
- **A later failure ends the reply early and says so** — "stopped after part
  3 of 7". Switching to a different voice halfway through would be worse
  than stopping in the one already playing.
- **Clicking Speak again stops the whole sequence**, not just the part
  currently sounding.

## Also in this build, from -b

The server-side synthesis timeout scales with text and always expires before
the browser's, so a timeout is reported by the side that actually knows what
the provider was doing.

**The reading-voice picker is English only.** It previously listed the best
voice for every installed language, which is why an English reply was read
in Danish. A preference saved before this change is honoured only if it can
read English; otherwise it is cleared automatically.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-c`.

On a long reply you should now hear the voice start within a couple of
seconds, and the note underneath should read "Played in their own voice
(7 parts)".
