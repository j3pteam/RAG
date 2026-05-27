# J3P Advisor Bot — with RAG Knowledge Base

A Flask chatbot with:
- Anthropic Claude for responses
- **RAG knowledge base** — upload PDF/DOCX/TXT documents, the bot retrieves relevant context before answering
- **Admin panel** at `/admin` — upload documents, view feedback, manage knowledge base
- **Feedback persistence** — thumbs up/down stored in Postgres for analysis
- **Voice input** via Web Speech API
- **Persona-configurable** via environment variables

## What's new vs the persona template

| Feature | How it works |
|---|---|
| Document upload | Drop a PDF/DOCX in the admin panel → auto-chunked, embedded, stored |
| Semantic retrieval | Each user message triggers a similarity search; top matches added to prompt |
| Feedback persistence | Thumbs up/down go to a Postgres table you can query |
| Admin dashboard | View feedback stats, manage docs, see helpful rate over time |

## One-time setup on Railway

This is a bit more involved than the previous bot because of the database.

### Step 1 — Push code to GitHub
Create a new repo, push all files. Existing repos work too; just replace contents.

### Step 2 — Create the Railway service
1. Railway → New Project → Deploy from GitHub repo
2. Pick your repo, Railway auto-detects Python

### Step 3 — Add Postgres database
1. In your project, click **+ Create** → **Database** → **Add PostgreSQL**
2. Railway provisions it and auto-injects `DATABASE_URL` into your service
3. **Important:** The database needs `pgvector` extension. Railway's Postgres includes it; the app auto-runs `CREATE EXTENSION IF NOT EXISTS vector` on first request. No manual setup.

### Step 4 — Set environment variables
On your web service, go to Variables tab and add:

**Required:**
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...          # for embeddings (~$0.50 to embed a 250-page book)
FLASK_SECRET_KEY=               # run: openssl rand -hex 32
ADMIN_PASSWORD=                 # any strong password for /admin access
```

**Persona (customize):**
```
PERSONA_NAME=J3P Advisor
PERSONA_OPENING=Hello, welcome to your session with the J3P Advisor.
PERSONA_PLACEHOLDER=How can I help you?
PERSONA_SYSTEM_PROMPT=<paste your full prompt here>
```

**Optional (sensible defaults exist):**
```
RAG_TOP_K=4                    # how many chunks to retrieve per query
RAG_MIN_SIMILARITY=0.3         # filter out weak matches (0–1)
ANTHROPIC_MODEL=claude-sonnet-4-6
MAX_TOKENS=1024
```

### Step 5 — Generate domain & first deploy
1. Settings → Networking → Generate Domain
2. Wait ~1 min for first deploy
3. Visit your URL — bot should load (without RAG context until you upload docs)
4. Visit `<your-url>/admin` and log in with `ADMIN_PASSWORD`

### Step 6 — Upload your first document
1. On `/admin`, use the upload form
2. Pick a PDF/DOCX/TXT/MD file (max 25 MB)
3. Wait — embedding takes ~5–30 seconds depending on doc size
4. You'll see it appear in the Knowledge Base table

That's it. The bot will now pull from your document automatically when relevant.

## How retrieval works

For every user message:

1. Message is embedded with OpenAI `text-embedding-3-small`
2. Top 4 most similar chunks are pulled from Postgres (HNSW index, very fast)
3. Chunks below `RAG_MIN_SIMILARITY` (default 0.3) are filtered out
4. If any pass the filter, they're appended to the system prompt under a "RELEVANT CONTEXT" section
5. Claude responds using that context plus the original persona prompt

When no chunks pass the threshold (e.g. user asks something off-topic), the bot answers from its persona alone — no degradation.

## Cost estimates (rough)

For a moderately busy bot with ~500 messages/month and 100 pages of documents:

| Item | Cost |
|---|---|
| Anthropic Claude (responses) | $2–8/mo |
| OpenAI embeddings (one-time + queries) | $0.50–2/mo |
| Railway Postgres (free tier) | $0 |
| Railway hobby plan | $5/mo |
| **Total** | **~$10/mo** |

Embeddings on uploads happen once. Per-query embedding cost is negligible (~$0.00002 each).

## File overview

```
app.py              Flask routes, chat, admin panel, retrieval orchestration
database.py         Postgres connection, schema, vector search, feedback
embeddings.py       Chunking, OpenAI embedding, PDF/DOCX extraction
requirements.txt    Python dependencies
Procfile / railway.json / runtime.txt    Deployment config
full_logo.png, monogram.jpg              Default brand assets
```

## Admin panel features

`/admin` (password-protected):
- **Feedback overview** — counts of up/down, helpful rate %
- **Upload form** — drag a file, give it a title, get it embedded automatically
- **Knowledge base table** — see all uploaded docs, chunk counts, delete unwanted ones
- **Recent feedback table** — last 50 ratings with full user question + bot reply

## Troubleshooting

**"Database not configured" warning on admin page**
→ Postgres plugin not added yet, or service hasn't picked up `DATABASE_URL`. Restart the service.

**"Cannot upload: RAG not fully configured"**
→ Missing `OPENAI_API_KEY` or `DATABASE_URL`.

**Upload succeeds but bot doesn't seem to use the content**
→ Check `RAG_MIN_SIMILARITY` — might be filtering too aggressively. Try lowering to 0.2.

**Admin page shows broken layout**
→ Check Railway logs for Python errors; most likely a missing env var.

## Privacy / safety notes

- Uploaded documents are stored in YOUR Railway Postgres — not sent to Anthropic for training
- Embeddings are computed by OpenAI; the chunks are sent to OpenAI's embedding endpoint (which per their policy is not used for training)
- Feedback rows include the verbatim user question and bot reply. Be mindful if sensitive info could be entered.
