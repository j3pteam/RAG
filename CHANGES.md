# J3P Advisor — build 2026-09-20-m

`app.py`, plus the pre-deploy checks. Includes everything from `-l`.

---

## Why the Word file did not match the screen

I opened the .docx you sent. It contains **76 paragraphs and zero tables**.
The Investment and Timing Summary tables arrived as single paragraphs of
pipe characters:

```
| Phase | Scope | Fee | |---|---|---| | Phase A: Leadership Alignment, …
```

So it is the opposite of what I first assumed. The page renders those tables
properly as of `-f`; the export does not, because `exports.py` builds
documents paragraph by paragraph and has no notion of a table. The screen
and the document have disagreed ever since the page learned to render them.

## What this build does

Tables are flattened into labelled blocks before the document is generated:

```
**Phase A: Leadership Alignment**
- Scope: Behavioral assessments, 360 feedback
- Fee: $68,000

**Total**
- Fee: $258,000
```

Every value survives, in order, and it reads as prose instead of debris.
Verified on your actual tables: all three fees, both scope descriptions,
every period and activity in the Timing Summary, and the sentence after the
table all present, with zero pipe characters left.

## This is a workaround, and I want to be clear about that

A real Word table has to be built by `exports.py`, which is the one file in
this project I have never had. Labelled blocks are readable and lossless,
but a proposal with a pricing table should have a pricing table.

**Send me `exports.py` and I will do it properly** — a real table in Word
and PDF, with the header row and column widths, rather than a good
approximation. It is a contained change to one function in that file.

---

## From -l

**Reply latency is measured.** Diagnostics → Reply times shows the last
twelve replies with the time broken down by phase — history, retrieval,
prompt, model call, post-processing — so "slow to respond" can be attributed
rather than guessed at.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-m`.
