# Standing up the same app under a new brand

Same code, same Railway account, new service and new database. The app is
identical; only environment variables differ.

Roughly twenty minutes, most of it waiting for a deploy.

---

## 1. Write the brand file

```
cp brands/TEMPLATE.env brands/theirname.env
```

Fill it in. The template says what each value reaches, and which are
required. Two that catch people:

- **`ORG_LEGAL_NAME`** is the entity named in the liability release
  participants accept. It is the one string here with legal weight — get it
  from their paperwork, not from their website header.
- **`ORG_NAMING_RULES`** should usually be **empty**. Empty is a real
  answer meaning "this firm has no names that could be confused with
  someone else's". Leaving the line out entirely is not the same thing, and
  the verifier will say so.

## 2. Verify it before it exists anywhere

```
./verify_brand.py brands/theirname.env
```

This does not check your list against another list. It **renders the real
participant page and the real system prompt** against those values and reads
what comes out.

```
  Meridian Advisory — clean.
     product:   Meridian Advisor
     entity:    Meridian Advisory LLC
     principal: Dana Cole
     contact:   clientservices@meridianadvisory.com

     No trace of the previous brand on the participant page or in the
     system prompt.
```

A half-finished rebrand fails and says exactly where:

```
   [the participant page] Residency Select
      …I release Residency Select LLC dba J3P Health, its coaches…
   [the system prompt] Alan Friedman
      …You are the Halcyon Advisor — a voice grounded in Alan Friedman's…
```

That second one is the case worth having a tool for: the participant page
looked perfect, and the advisor would still have introduced itself as
grounded in your thinking.

**Writing this check found three real leaks in the code** that reading it
had not: the first paragraph of the liability release, the download filename
(`j3p_response.docx` landing in a client's downloads folder), and a CSS
comment. All three are fixed. Expect it to find more as the app grows —
that is what it is for.

## 3. Create the service

In the existing Railway account:

- New service from the same repository
- Add a Postgres database to it
- Paste the brand file's variables in, plus:
  - `FLASK_SECRET_KEY` — generate a fresh one, never reuse another
    deployment's: `python3 -c "import secrets; print(secrets.token_hex(32))"`
  - `DATABASE_PRIVATE_URL` — Railway's internal Postgres address
  - `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `ADMIN_PASSWORD`
  - `SAFETY_ALERT_EMAIL` — someone at **their** organization

## 4. Confirm on the running deployment

Read the startup log first. It names any brand value still left at the house
default. Then:

- [ ] Diagnostics → no FLASK_SECRET_KEY banner
- [ ] Diagnostics → Database connections shows `.railway.internal`
- [ ] Open a session — greeting, footer and release all name them
- [ ] Ask the advisor **"who are you?"** — the answer should name their firm
      and their principal, and nothing of yours
- [ ] Download a response — the filename carries their name

## 5. Load their knowledge base

Theirs only. Nothing carries across: separate database, separate content.

---

## Why a separate database

Their transcripts are not in your database, and yours are not in theirs.
There is no query that could cross between them, because there is nothing
to cross to. That is a stronger answer for a client's security review than
any isolation logic inside a shared system, and it costs one extra Postgres
instance.

It also means a brand can be updated, paused or handed over without touching
any other.

---

## Updating them all

One repository, several deployments. Deploy per service, in whatever order
you like — a brand can stay on an older build if it needs to.

Run `check.sh` before any deploy, and `verify_brand.py` for each brand after
any change to participant-facing copy. All five checks and the brand
verifier exist because something shipped wrong without them.

---

## Still missing, for any brand

Deletion on request, an access audit trail, and retention. These are not
branding — they apply to every deployment equally, and a client's security
review will ask about all three.
