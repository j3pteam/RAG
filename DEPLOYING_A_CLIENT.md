# Deploying the Advisor for a client

Option A: you host, one deployment and one database per client. Written as a
checklist because a new client deployment should not depend on anyone
remembering how the last one went.

---

## Why one deployment each

Their data is in their own database. There is no query that could return
another client's transcripts, because another client's transcripts are not
in there. That is worth more to a healthcare buyer's security review than
any isolation logic inside a shared system, and it is the reason this is
the right first shape for the product.

The cost is that each client is a deployment you maintain. That is fine at
five and a problem at fifty; revisit when the number of clients makes it so.

---

## 1. Create the infrastructure

- New Railway project, named for the client
- Add Postgres to it
- Deploy the app from the repository

## 2. Set the environment

**Branding — every one of these, or the app warns at startup:**

| Variable | Example | What it reaches |
|---|---|---|
| `ORG_NAME` | `Meridian Advisory` | Citations, share text |
| `ORG_SHORT` | `Meridian` | In-session references to the firm |
| `ORG_LEGAL_NAME` | `Meridian Advisory LLC` | The liability release participants accept |
| `ORG_PRINCIPAL` | `Dana Cole` | Whose thinking the persona is grounded in |
| `PERSONA_NAME` | `Meridian Advisor` | The product's name throughout |
| `CONTACT_EMAIL` | `hello@meridian.com` | Where participants are sent for help |
| `ORG_NAMING_RULES` | *(empty string)* | Entity-name disambiguation; most firms need none |

**Operational — two of these are not optional:**

| Variable | Why |
|---|---|
| `FLASK_SECRET_KEY` | **Required.** Unset, each worker signs cookies with its own key: sign-ins drop at random and every redeploy signs everyone out |
| `DATABASE_PRIVATE_URL` | **Strongly recommended.** Without it the app reaches Postgres over the public proxy, adding hundreds of milliseconds to every round trip |
| `ADMIN_PASSWORD` | Their administrator's initial access |
| `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY` | Model and embeddings |
| `ELEVENLABS_API_KEY` | Only if they want voice cloning |
| `SAFETY_ALERT_EMAIL` | Who receives participant-safety alerts — **must be someone at the client**, not J3P |

## 3. Verify before handing over

Start the deployment and **read the startup log**. It states plainly which
brand settings are still J3P's. Zero warnings is the bar.

Then, in the app:

- [ ] Open a session. The greeting names their product, not the J3P Advisor
- [ ] Open the release. It names **their** legal entity
- [ ] Ask "who are you?" — the answer names their firm and their principal
- [ ] Ask something off-topic — the decline names their firm
- [ ] Diagnostics → no FLASK_SECRET_KEY banner
- [ ] Diagnostics → Database connections shows a `.railway.internal` host
- [ ] Diagnostics → Version matches what you deployed

## 4. Load their knowledge base

Their documents only. Nothing from J3P's base carries across — separate
database, separate content.

## 5. Hand over

- Admin URL and their administrator's credentials
- Who to contact, and what response time you are committing to
- What you will do when you deploy an update, and how much notice they get

---

## Updating a client

The repository is shared; the deployments are separate. An update is a
deploy per client, in whatever order you choose — which also means a client
can stay on an older build if they need to.

Run `check.sh` before any deploy. All five steps exist because something
shipped broken without them.

---

## What this does not yet cover

Named honestly, because a client's security review will ask:

- **Deletion on request.** No way to remove one participant's data.
- **Access audit trail.** No record of which staff account read which
  transcript.
- **Retention.** Nothing expires: transcripts, participant links and
  uploaded documents persist until deleted by hand.

These are the next pieces of work, and they are the same three whichever way
the product is eventually sold.
