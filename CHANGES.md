# J3P Advisor — build 2026-09-18-f

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

Includes the `-e` log fix, so deploy this whether or not you took that one.

---

## Session transcripts can be scoped to assigned advisors

Before this, `view_conversation_log` was `True` for **owner, admin and
viewer alike**, with no per-advisor filtering anywhere. Any account of any
role could read every session with every participant across every advisor.
For psychological assessment and employment material, with client
organisations sometimes being the participant's own employer, that default
was not defensible.

**Manage Users now has a "Sessions they can read" column.** Select one or
more advisors and that account sees only those sessions. Select none — the
default, and what every existing account keeps — and nothing changes for
them.

Enforcement is in two places, deliberately:

- The advisor filter on the Activity tab lists only advisors in scope, so
  an out-of-scope advisor cannot be reached by editing the URL.
- Rows are filtered again after the query, so an account viewing "all
  advisors" still only sees its own. Applied in the route rather than
  inside SQL, so the rule is readable where it is enforced.

Verified: unrestricted accounts see all four test sessions; an account
scoped to one advisor sees one; scoped to two sees two.

**Owners are never scoped.** Someone has to be able to see everything, and
hiding data from the account that administers the system is containment in
appearance rather than in fact.

**One behaviour worth knowing:** sessions on the default persona belong to
no advisor, so they fall outside every scope and a restricted account will
not see them. That is the safe direction, but it means a scoped coach will
not see main-link sessions even if you expected them to.

## Existing accounts are unaffected

The column defaults to empty, which means unrestricted. Nobody loses access
on deploy. Scoping is something you turn on per person.

---

## Also in this build (from -e)

**Participant text no longer goes into the deploy logs.** The grounding
check in `-d` wrote each participant's question into the application log.
Deploy logs are retained by the host, readable by anyone with project
access, and outside the database's access controls and deletion paths. The
line now carries only the score, verdict and source titles.

---

## Still open, from the privacy conversation

1. **No audit trail** — you cannot answer "who at J3P read my session?"
2. **No retention policy** — nothing is ever deleted
3. **No participant deletion path** — a deletion request needs SQL today
4. **Participant links never expire**
5. **360 documents contain third parties** who never consented to being in
   the system

I would take the audit trail next: for HR material, being unable to answer
who read what is the gap most likely to matter in a dispute, and it is
cheap to add now that scoping exists.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-18-f`.

After deploying: Manage Users, pick a non-owner account, assign one advisor,
sign in as them and confirm the Activity tab shows only that advisor's
sessions.
