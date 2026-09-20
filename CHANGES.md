# J3P Advisor — build 2026-09-20-d

`app.py`, plus the pre-deploy checks.

---

## Turning Speak off now actually stops the sound

My bug. The Speak toggle called `J3PSpeech.stop()`, which stops the
**browser's** speech engine. The advisor's cloned voice is a different
mechanism entirely — an `<audio>` element playing a file fetched from the
server — and nothing told it to stop. So switching Speak off silenced a
voice that was not the one talking.

Chunked playback, added in `-c`, made it worse: the sequence would keep
fetching and playing the remaining parts.

**Every stop path now goes through one function** that halts both the
browser voice and the cloned voice, cancels any pending parts, and clears
any audio left over from an earlier reply. The Speak toggle, clicking the
avatar, and clicking Speak on another reply all use it.

## A second fault found while fixing it

The chunk sequence detected "the participant stopped this" by listening for
the audio element's `pause` event. But swapping `audio.src` between parts
can itself fire `pause` — so a long reply would have ended at the first
join, reporting "stopped after part 1 of 7" for no reason.

Replaced with an explicit cancel that only a real stop triggers. Verified
both ways: a three-part reply plays through to the end, and a stop during
part 2 of four cancels the sequence, fetches nothing further, and releases
the audio.

I should have caught this in `-c` — inferring user intent from a media event
that the code itself also triggers was the wrong approach from the start.

---

## From -c and -b

**The cloned voice is synthesised in parts**, so playback starts within a
couple of seconds on a long reply instead of waiting for the whole thing —
and no reply is long enough to time out. **The reading-voice picker is
English only**, which is what caused the Danish. **The server-side synthesis
timeout scales with the text** and always expires before the browser's.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-d`.

Worth testing directly: start a long reply speaking, then press Speak again
part-way through. It should stop immediately and stay stopped.
