# J3P Advisor — build 2026-09-20-l

`app.py`, plus the pre-deploy checks. Includes everything from `-k`.

---

## Reply latency is now measured

The chat route had **no timing at all** — only admin page loads were
instrumented. So "taking a very long time to respond" had nothing behind it,
and I would have been guessing between the model, retrieval, history, the
database and the voice.

Every reply is now timed by phase:

- request parsed and attachments read
- conversation history loaded
- knowledge retrieval (embedding + search)
- prompt assembly
- **model call**
- reply post-processing (scrubbers, formatting)

**Diagnostics → Reply times** shows the last twelve, newest first, with the
total coloured by severity and the breakdown beside it:

```
23:33:59   14.2s   request parsed 12ms · history 48ms · retrieval 610ms ·
                   prompt 3ms · model call 13400ms · post-processing 160ms
```

The same line goes to the deploy logs as `[timing] /chat: …`.

## What to expect, and what it would mean

The model call is normally the great majority of it, and that is Anthropic
generating the reply — a long proposal legitimately takes ten to twenty
seconds and no change here would alter that. **If the model call dominates,
the latency is inherent.**

What would be worth acting on is anything *else* being large:

- **retrieval** over a second — the embedding call or the vector search,
  which is fixable
- **history** over a second — the conversation is being re-read from the
  database on every turn
- **post-processing** over a second — the scrubbers, which run over the
  whole reply

Send a message, open Diagnostics, and tell me what the row says. That turns
this into one specific thing rather than another round of guesses.

One note: the figures are per worker, and there are two. A reply handled by
the other worker will not appear — reload once or send a second message if
the table looks empty.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-l`.
