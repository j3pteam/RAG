# J3P Advisor — build 2026-09-20-a

`app.py`, plus the pre-deploy checks.

---

## Open a conversation from the log

A log row is one exchange out of a session. Reading one exchange out of
context has been the only option because nothing joined a row to the
conversation it came from — the log records exchanges, `chat_history` holds
threads keyed by participant token, and the two had no link.

**The question in each row is now a link.** It opens the whole conversation,
oldest first, with who it was with and how many messages.

Two decisions worth stating plainly:

**It is read-only.** Reading a session and continuing one as the participant
are different acts — the first is what the conversation log already permits,
the second is impersonation and would put words in their mouth. If you want
an advisor to be able to pick up a thread, that should be built knowingly
rather than arrive as a side effect of a "view" button. The page says so.

**Advisor scoping is enforced here too.** An account restricted to certain
advisors cannot reach another advisor's conversation by editing the id in
the URL. Opening one is logged with the admin's email.

**This works from now on, not backwards.** The link between an exchange and
its conversation is recorded as exchanges happen, so sessions logged before
this build will say so rather than show an empty page.

---

## Export and import advisors

Advisors tab → **Export or import advisors**.

The export is the roster — name, slug, scheduling URL, booking-button
setting, session link, and counts for participant links, documents, voice
sample and portal link. CSV or Excel.

It is the same shape the importer reads, so an edited export uploads
straight back. Matching is by name, so a row for an existing advisor updates
them rather than creating a duplicate.

Only **Name** is required; Scheduling URL and Booking button are optional.
Slug is deliberately ignored on import — it is derived from the name, and
letting a file set it would allow two advisors to collide or an existing one
to be silently repointed. **Photos, voice samples and knowledge are never
touched by an import**, because a spreadsheet cannot carry them and clearing
them would quietly wipe work done in the panel.

Verified against a file with a quoted comma in a name, a blank row, and
missing optional columns; a file with no Name column and a wrong file type
are both rejected with a message that says what to fix.

*(This completes work I started and left half-finished last turn — the
parsing helpers were in the file with nothing calling them.)*

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-a`.

Run `./check.sh` first — it now covers syntax, undefined names, module-level
definition order, and HTML well-formedness across all eight tabs.
