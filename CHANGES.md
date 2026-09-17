# J3P Advisor — build 2026-09-17-d

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## The voice disconnect

The admin panel shows Alan Friedman's sample present, consented, cloned,
"Everything needed is in place". `/a/alan-friedman` says no sample exists.
Both are telling the truth about different records.

Every advisor's voice sample is keyed by **slug**. The default persona —
the one on the main link — has its own slug and its own Voice Sample
section. Its heading uses whatever display name you gave the default
advisor. Set that to "Alan Friedman" and two different records produce two
sections that read identically:

- `__default_persona__` — used by `/` and `/scheduling`
- `alan-friedman` — used by `/a/alan-friedman/...`

A recording saved against the first looks completely healthy in the admin
panel and is invisible to the second. Nothing was erased.

### Confirming it

`/health` → `advisor_voice` → `with_sample`. The slug carrying the
recording is named there, and the default persona now identifies itself as
"the default persona (main link)" rather than as an unknown slug.

### Fixing it without re-recording

Each Voice Sample section now states which record you are looking at:

> Attached to `alan-friedman` — used by sessions at `/a/alan-friedman`.

or

> Attached to `__default_persona__` — the default persona, used on the main
> link. Sessions at `/a/<advisor>` do not use this recording.

And where a sample exists there is a **"Wrong advisor? Copy this recording
to another"** control. Pick the destination, and consent, tuning and voice
mode travel with it. `provider_voice_id` does not — the cloned voice at
ElevenLabs is registered against the advisor it was built for, so it
re-clones on next use.

It copies rather than moves. The original stays put; removing it is a
separate deliberate act. Whatever the destination already had is archived
first.

So: if the recording is on `__default_persona__` and you want it on
`alan-friedman`, open the default persona's Voice Sample section, copy it
to Alan Friedman, and Preview should then play his voice.

---

## Also in this build

**Voice samples are no longer destroyed on save** (2026-09-17-c). The save
path ran `DELETE` then `INSERT`, so the recording existed only in memory in
between, and a failure there — silently swallowed — lost it. It is an
upsert now, with no moment where the advisor has no sample. Replacements
and removals are archived, last five per advisor, restorable from a
"Previous recordings" panel.

**`/health` reports advisor voice state** (2026-09-17-b) — every advisor,
every slug with a sample, consent, cloned, mode, size.

**Preview Voice reports which voice it used and why** (2026-09-17-a).

---

## From build 2026-09-16-j

**Admin panel.** Atlassian design language in J3P colours; sentence case
and larger type; contrast-checked status colour. One tab per request —
Overview 553 KB → 71 KB. Advisor detail in five bulk queries rather than
five per advisor. Per-advisor participant links with bulk CSV/XLSX upload
and export. Automatic learning toggle merged into Continuous Learning.
Copied links are https.

**Participant chat.** The "Error: Unknown error" bug. The cloned voice
timing out on long replies. The idle prompt interrupting typing. The
duplicate feedback box.

---

## Installing

Replace `app.py`, commit to `main`. Railway rebuilds on push. Check
`/health` reports `"version": "2026-09-17-d"`.

`admin-atlassian.css` and `admin-refresh.css` in the repo root are dead
files; the CSS is inlined in `ADMIN_HTML`. Safe to delete.
