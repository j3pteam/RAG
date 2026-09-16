# What's in this package, and what to do with it

This is a **drop-in for the existing `j3pteam/RAG` repository**, not a
complete copy of it. Everything here either changed or is new. Files you
already have and that I never modified are deliberately absent — see
"Not included" below.

Current build: **2026-09-16-i**

---

## Files

```
app.py                  REPLACES the existing file
tenant.py               new
tenants/j3p.json        new
tenants/example.json    new
WHITE_LABEL.md          new
```

### app.py
One file, all the changes from this session:

- Admin panel restyled on the Atlassian design language in J3P brand colours,
  with a status palette checked for contrast (4.6–7.6:1 against its own tints)
- Admin renders one tab per request instead of all seven — the page you're
  looking at dropped from 553 KB to 71–246 KB depending on tab
- Advisor detail reads in five bulk queries instead of five per advisor
- Per-advisor participant links, with bulk CSV/XLSX upload and export scoped
  to one advisor
- Idle prompt waits for genuine inactivity rather than interrupting typing
- Feedback comment box can no longer be duplicated by a double-tap
- Contact scrubber can no longer empty a reply (the "Unknown error" bug)
- Cloned voice no longer times out on long replies; clips are cached
- All client-specific values now read from `tenant.py`
- Activity tab: the automatic-learning toggle now sits inside
  Continuous Learning rather than in its own card

### tenant.py
The white-label layer. Loads `tenants/<TENANT>.json`, falling back to J3P's
values for anything missing so an incomplete file can't break a deployment.

### tenants/j3p.json
J3P's own configuration, generated from the defaults in `tenant.py` so the
two can't drift. Your current deployment reads this.

### tenants/example.json
Annotated template for a new client. Copy to `tenants/<slug>.json` and edit.

### WHITE_LABEL.md
How to stand up a second client, what each config field does, and an honest
list of what still says "J3P" in the code.

---

## Installing

**GitHub web UI.** Open `app.py` in the repo, click the pencil, select all,
paste the new version, commit to `main`. For the rest use **Add file →
Create new file**; for the tenant files type the path as
`tenants/j3p.json` — typing the slash creates the folder.

**Locally.** Unzip over your clone, `git add -A`, commit, push.

Either way Railway redeploys on push. `railway.json` already pins the start
command and health check, so there's nothing to configure.

### Verifying

Open `/health`. You want:

```json
"version": "2026-09-16-i",
"tenant": { "tenant": "j3p", "config_file_present": true, ... }
```

`config_file_present: false` means `tenants/j3p.json` didn't land where the
app expects it. The app still runs — it falls back to the built-in J3P
values — but the white-label layer isn't actually wired up yet.

Then click through all seven admin tabs. The tab change moved every pane
behind a server-side conditional, and a mistake there blanks a tab rather
than throwing an error, so it's worth thirty seconds of clicking.

---

## Not included

I only ever had `app.py`, so these are untouched and not in the package —
don't let the absence suggest they should be deleted:

```
database.py  embeddings.py  paywall.py  exports.py  system_prompt.py
requirements.txt  Procfile  railway.json  README.md
full_logo.png  monogram.jpg  advisor_avatar.jpg
advisor_idle.mp4/.webm  advisor_placeholder.mp4/.webm
patch_participant_links.py  document-advisor-assignment.patch
```

`Procfile` and `railway.json` I've read but not modified. They're correct
as they stand, and a second Railway service picks both up automatically.

---

## Worth deleting while you're in there

`admin-atlassian.css` and `admin-refresh.css` are drafts I sent before you
uploaded `app.py`. The CSS is now inlined in `ADMIN_HTML` and nothing loads
either file. Leaving them invites someone to edit one later and wonder why
nothing changes.

---

## One thing to know about the deployment

`railway.json` runs gunicorn with `--workers 2`, so the in-process caches —
compiled templates, synthesised voice clips, settings — exist once per
worker. Nothing breaks; cache hit rates just look like about half what
you'd expect. It's also why the learning scheduler claims its slot through
the database rather than trusting a process-local flag.
