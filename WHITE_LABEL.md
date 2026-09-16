# White-labelling the advisor

How to stand up this application for a client other than J3P.

---

## The shape of it

**One deployment serves one client.** A new client means a new Railway
project, its own Postgres, its own environment variables, and one JSON file
describing the brand. It does *not* mean a `tenant_id` column and a shared
database.

That is a deliberate choice, and worth understanding before you commit to it.
This application stores coaching transcripts, personality self-reports, 360
feedback documents and biometric exports. Making it multi-tenant means adding
a tenant column to roughly twenty tables and a filter to every query that
touches them — and from then on, one forgotten `WHERE tenant_id = ...` shows
one client another client's participants. Separate databases make that
mistake impossible rather than merely unlikely. The price is a second Railway
project per client, which is far cheaper than the incident it prevents.

The trade-off changes if you ever reach dozens of clients. At that point the
operational cost of many deployments starts to outweigh the isolation, and
the honest answer is a rebuild with tenancy designed in from the start — not
a column bolted onto this schema.

---

## What a client actually gets

Their own branding, their own advisors, their own knowledge base, their own
participants, and their own conversation history. Nothing is shared between
deployments, including the vector store — the knowledge base is per-database,
so a client's uploaded documents are only ever retrieved for their own
advisors.

---

## Standing one up

### 1. Write the tenant file

Copy `tenants/example.json` to `tenants/<client-slug>.json` and work through
it top to bottom. The file is annotated; four fields are marked REVIEW and
deserve real attention:

| Field | Why it matters |
|---|---|
| `brand` | Four colours drive the whole interface. The admin stylesheet derives its neutrals from `paper`, so the greys stay coherent with whatever you choose. |
| `expertise` | Dropped verbatim into the scope guard. This is what the model uses to decide whether a question is in scope. Too narrow and it refuses reasonable questions; too broad and it becomes a general-purpose assistant with a client logo on it. |
| `staff` | Names here are treated as referrals to individuals: any passage naming one alongside contact language is replaced with the client services address, so the AI never routes a participant to someone's personal calendar. |
| `release_body` | The liability release every participant accepts. **Send it to the client's counsel.** Shipping on J3P's wording would name J3P's legal entity in another company's product. |

Anything you omit falls back to J3P's value. That is a safety net so a
half-finished file cannot break a deployment — it is not a plan. A field you
forget prints J3P's wording to this client's participants.

### 2. Add the brand assets

Drop the image files next to `app.py` and point `assets` at them:

- `logo_url` — the header lockup, shown at ~60px tall
- `favicon_url` — browser tab mark
- `avatar_url` — the default advisor photo, square, 320px+
- `avatar_loop_url` — optional looping portrait clip; `""` for a still photo

Named advisors upload their own photos through the admin panel, so these are
only the defaults.

### 3. Create the deployment

New Railway project, new Postgres plugin, then:

```
TENANT=<client-slug>          # selects tenants/<client-slug>.json
DATABASE_URL=...              # set automatically by the Postgres plugin
ANTHROPIC_API_KEY=...
VOYAGE_API_KEY=...            # embeddings for the knowledge base
FLASK_SECRET_KEY=...          # generate fresh; never reuse across clients
ADMIN_PASSWORD=...            # break-glass owner login for first sign-in
```

Optional, per client:

```
ELEVENLABS_API_KEY=...        # advisor voice cloning
POSTMARK_SERVER_TOKEN=...     # sign-in links, safety alerts, briefings
PUBLIC_BASE_URL=https://...   # custom domain, if they have one
SAFETY_ALERT_EMAIL=...        # overrides alert_email in the tenant file
```

`FLASK_SECRET_KEY` must be unique per client. It signs session cookies and
seeds the participant-link tokens; reusing one across deployments would make
tokens from one client valid at another.

### 4. Verify before handing it over

Load `/health`. It reports which tenant is live:

```json
"tenant": {
  "tenant": "acme-health",
  "org_name": "Acme Health Partners",
  "persona_name": "Acme Advisor",
  "config_file_present": true,
  "staff_configured": 2,
  "forbidden_names": 2
}
```

`config_file_present: false` means the slug didn't match a file and the
deployment is silently running J3P's branding. That is the single most
likely mistake, and it is why the field exists.

Then walk the checklist:

- [ ] Open the participant chat — logo, colours, greeting, footer all correct
- [ ] Accept the release gate and read it — client's legal entity, not J3P's
- [ ] Ask something clearly out of scope; confirm the decline names the client
- [ ] Ask "how do I get in touch?" — confirm it returns their client services
      address and no individual's name
- [ ] Sign into `/admin`, create an advisor, upload a document, ask something
      that should retrieve it
- [ ] Issue a participant link and open it in a private window

### 5. First admin account

Sign in at `/admin` with `ADMIN_PASSWORD`, then create a real owner account
under Manage Users. `ADMIN_PASSWORD` stays as break-glass access if every
individual password is lost.

---

## What is not yet in the tenant file

Honest list of what still says J3P in the code, and what each would take.

**UI copy in the admin panel and advisor portal.** Roughly thirty strings —
"Also share with J3P so the team can review it", "This stays private to J3P's
team", and similar. These are staff-facing, not participant-facing, so a
client's *participants* never see them; their *administrators* would. Fixing
this means threading `TENANT["org_short"]` through the templates. Worth doing
before a client's own staff administer their own instance.

**The system prompt's voice rules.** `system_prompt.py` and the voice guard
encode J3P's house style — the vocabulary bans, the "say the hard thing"
rule, the specialty-assumption rules written for physician audiences. These
are good defaults for any coaching product, but they are J3P's opinions. A
client with a different voice needs their own `PERSONA_SYSTEM_PROMPT_FILE`.

**The assessments.** The TIPI personality inventory and the behavioural
self-assessment are generic instruments, not J3P-specific, so they transfer
as-is. The interpretation copy is written for leadership coaching.

**The knowledge base is empty on day one.** There is no seeding mechanism.
The client uploads their own documents through the admin panel, the advisor
portal, or the email ingestion webhook.

---

## Keeping clients in sync

All clients run the same `app.py`. A fix deployed to one should be deployed
to all — there is no per-client code, by design. If you find yourself wanting
to fork the code for one client, add a tenant field instead; a fork is a
second codebase to maintain and it will drift.

`tenants/j3p.json` is generated from the defaults in `tenant.py`, so the two
cannot disagree. If you change a default, regenerate that file.
