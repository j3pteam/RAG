# J3P Advisor — build 2026-09-24-h

`app.py`, the pre-deploy checks, and **`patch_exports.py`** — a one-time
script that edits your `exports.py`.

---

## First: I made a mistake while working on this

Hunting for `exports.py` on disk, I ran `cp /mnt/user-data/uploads/*.py .`,
which overwrote my working copy of `app.py` with a version of it from
**September 15**. I then "found" three bugs in that file and told you about
them. Two were not real:

- the missing table flattening — present in your build all along
- a stray `</label>` in Participant Access — not in your build
- a `NameError` on oversized uploads — not in your build either

I restored from the packaged `2026-09-24-g` and re-applied only the genuine
change. Nothing from that detour is in this build. Disregard that part of my
last message.

---

## Internal documents keep the firm's own names

You were right that this was in `exports.py`. `build()` calls
`scrub_brand()` on every document, and that function does not merely remove
the names — it **drops whole lines** whose remainder is under 12
alphanumeric characters, and leaves holes in the ones it keeps:

```
before   The fixed retainer provides priority access to J3P Health's full practice.
after    The fixed retainer provides priority access to 's full practice.

before   - Access to J3P Health's broader cadre of specialists
after    - Access to 's broader cadre of specialists

before   - J3P Health
after    (the bullet is gone)
```

Two changes, both in `patch_exports.py`:

**`build()` takes `scrub=True`.** The caller decides, because only the
caller knows whose session it is. `app.py` now passes `scrub=False` when the
advisor is internal, exactly as `chat()` already bypasses its own scrubber.

**Scrubbing replaces rather than deletes.** A client deliverable now reads
"access to our practice's full practice" instead of "access to 's full
practice". Still not elegant, but it is a document rather than visibly
broken output that the client sees and you do not.

The drop-the-line test is unchanged in effect — it is judged on what
deletion would leave, so a bullet that is only a brand name still goes.

## Installing

1. `python3 patch_exports.py` from the repo root. It writes
   `exports.py.bak` first, verifies the result parses, and **refuses to
   write anything** unless all four edits match exactly — so a
   half-patched file is not a possible outcome. If your `exports.py` has
   moved on from the version I was given, it will say so and change
   nothing.
2. Replace `app.py`.
3. Commit both. Diagnostics should report `2026-09-24-h`.

## Still outstanding from that file

Real Word **tables** — `parse_blocks` has no table concept, so the
flattening workaround stays for now. That is a contained addition to
`parse_blocks` plus the docx and pdf renderers, and I would rather do it as
its own change than bundle it with a fix you are waiting on.

`list_documents` at ~460 ms is `database.py`, not this file.
