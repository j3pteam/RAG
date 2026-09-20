# J3P Advisor — build 2026-09-20-g

`app.py`, plus the pre-deploy checks. Includes everything from `-f`.

---

## The avatar status is just the status again

It read `SPEAKING (THEIR OWN VOICE)` — and on a fallback, the whole error
message in capitals beside a participant's session. That detail was added
while chasing the voice bug. It did its job and became clutter.

```
Ready
Thinking
Responding
Speaking
```

No detail on any of them.

**The explanation is still there**, in the note under the reply, where it
can be read at leisure rather than flashing past under the avatar — "Played
in their own voice", or "Played in the default voice — …" with the reason
when something fell back. That is the right home for it: it belongs to the
reply it describes, and it does not shout.

I also dropped the "(28 parts)" from that note. Same category — how many
requests the synthesis took is my business, not the participant's.

---

## One thing worth raising

That reply was **28 parts**, so roughly 19,000 characters — each part its
own call to ElevenLabs. It works, and playback starts quickly, but it is a
lot of requests for one reply and it will show up in usage.

Raising the chunk size from 700 to around 1,200 characters would cut the
call count by about 40% while still starting playback in a couple of
seconds. I have not changed it, because it trades slightly against how fast
the first part arrives and that is your call rather than mine. Say the word
either way.

---

## From -f and -e

**Markdown tables render as tables** rather than a wall of pipes — the
Investment table in your earlier screenshot. **Stopping speech pauses every
`<audio>` element on the page**, including any this code has lost track of.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-g`.
