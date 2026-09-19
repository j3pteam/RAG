# J3P Advisor — build 2026-09-19-i

`app.py`, plus the pre-deploy checks.

**Includes the private-database-address change from `-h`** — the one that
addresses the slowness. Deploy this.

---

## Every tab now behaves the same way

Sections collapse and open on click, each with its own summary line:

**Knowledge**
```
▸ Find research            PubMed and OpenAlex · 2 results
▾ Documents                30 embedded
▸ Upload Document          PDF, Word, text or Markdown
▸ Upload Folder            many files at once
▸ Add Knowledge from URL   fetches and embeds a web page
▸ Add Knowledge from Text  paste directly
```

**Manage Users**
```
▸ Signed in as             Alan Friedman · owner
▸ Add a user               invite an administrator
▾ Existing users (2)       2 accounts
```

**Biometric data**
```
▸ Upload a file            Apple Health, Oura, Whoop exports
▾ Files                    3 files
```

**Settings** — Participant Access collapses; the rest of that tab is one
form and was already compact.

In each case the section people arrive for stays open — Documents,
Existing users, Files — and the actions that create new things start
closed, since they are occasional.

## Two tabs left alone, deliberately

**Overview** is a single card of four numbers. A collapsible wrapper round
one card is cost without benefit.

**Diagnostics** exists to be read all at once when something is wrong.
Making someone open six sections to find which one is red would defeat what
it is for. Say the word if you would rather it matched anyway.

**Advisors** already worked this way — one card open at a time, from `-f`.

---

## Still the main thing

`-h` added automatic use of Railway's private database address. Until that
variable is set, Diagnostics → Database connections will show:

```
Database address   roundhouse.proxy.rlwy.net
                   public proxy — every connection leaves the datacentre
```

Measured: two queries on an open connection take 68 ms; two that each open
one take 2.2 seconds. Setting `DATABASE_PRIVATE_URL` on the web service is
what closes that gap, and no code change achieves the same.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-19-i`.
