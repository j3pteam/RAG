# J3P Advisor — build 2026-09-20-b

`app.py`, plus the pre-deploy checks.

---

## Two faults, and the screenshots showed both

### "synthesis-error: the read operation timed out"

The server waited a flat **30 seconds** for ElevenLabs, whatever the length
of the text. That is plenty for the one-sentence preview — which is why
Preview reported "Playing Alan Friedman's own voice" — and not enough for a
full coaching reply. The read timed out, and the participant got the browser
voice instead.

The wait now scales with the text, from 12 seconds for a preview to 55 for a
long reply.

It is also deliberately kept **below** the browser's own ceiling, so the
server is always the one that decides it has waited long enough:

| Reply | Server waits | Browser waits | Gives up first |
|---|---|---|---|
| 80 chars | 12s | 14s | server |
| 500 chars | 18s | 27s | server |
| 1,500 chars | 38s | 57s | server |
| 3,000 chars | 55s | 60s | server |

That ordering matters: a browser-side abort tells us nothing about what the
provider was doing, while a server-side timeout is logged with the text
length and the elapsed time.

### It spoke Danish

This one is a design fault of mine, not a glitch. The reading-voice picker
listed **the best voice for every language installed on the device** —
Danish, Finnish, Japanese, Russian. Any of them could end up selected, and
selecting one meant an English reply was read in that voice.

Advisors write in English. The useful choice is between English voices, not
between languages. The picker now lists up to eight English voices, best
first:

```
English (US)  Samantha
English (AU)  Karen
English (US)  Alex
English (GB)  Daniel
```

A preference saved before this change could still be a Danish voice, so a
saved choice is now honoured only if it can actually read English;
otherwise it is cleared and the automatic English pick is used. Nobody has
to go and fix their own setting.

---

## From build 2026-09-20-a

**Open a conversation from the log** — the question in each row links to the
whole session, read-only, with advisor scoping enforced. **Export and import
advisors** as CSV or Excel.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-b`.

Worth retrying afterwards: the same long reply that failed. If it still
falls back, the status note under the reply will say whether the provider
errored or the wait was still too short — and the server log now records the
character count and the elapsed milliseconds alongside it.
