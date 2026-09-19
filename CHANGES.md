# J3P Advisor — build 2026-09-18-g

One file: `app.py`. Replaces the existing one in `j3pteam/RAG`.

---

## Literature search: PubMed and OpenAlex

Knowledge tab → **Find research**. Type a query, get merged results from
both services, and add any paper's abstract to the knowledge base with one
click.

Both are free and need no API key.

**This is admin-side only, and that is the point.** Nothing a participant
types is ever sent to either service. This builds the corpus the advisor
answers from; it does not let the advisor answer from the open web. Putting
search in the participant path would undo the scope guard, undo the
grounding check, and send coaching questions to a new vendor — the opposite
of last week's privacy work.

### What it stores

The abstract, not the full paper — that is what the APIs return, it is
unambiguously free to hold, and it carries the finding. The citation and
source URL go in with it, so an advisor's answer can be traced back.

Each result can be assigned to one advisor or shared with all, using the
same ownership control as any other document.

### Details that matter in practice

**Structured abstracts keep their labels.** PubMed returns Background,
Methods, Results as separate elements; the labels are preserved because
they chunk better than a flattened paragraph.

**OpenAlex abstracts are rebuilt.** OpenAlex stores them as a word-position
map rather than text, so they are reconstructed on the way in. Without
that, OpenAlex results would carry no abstract at all and be worthless to
ingest.

**Duplicates are merged on DOI**, with the PubMed copy preferred — its
abstracts are cleaner and structured ones keep their sections. The same
paper is in both services routinely.

**Both services are told who is calling.** NCBI raises the rate limit for
identified callers and OpenAlex routes them to a faster pool. It uses your
contact address, or `RESEARCH_CONTACT_EMAIL` if you set one.

Verified against representative payloads: italic markup inside titles,
structured-abstract labels, inverted-index reconstruction, DOI
de-duplication across sources.

---

## Also in this build

**Session transcripts can be scoped to assigned advisors** (`-f`). Manage
Users → "Sessions they can read". Every existing account stays unrestricted;
scoping is turned on per person.

**Participant text no longer goes into the deploy logs** (`-e`).

**Replies are checked back against the knowledge base** after generation
(`-d`), with results in Diagnostics → Answer grounding.

---

## Still open from the privacy list

1. No audit trail — "who read my session?" is unanswerable
2. No retention policy — nothing is ever deleted
3. No participant deletion path
4. Participant links never expire

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-18-g`.

First search to try: something you already know the literature on, so you
can judge the result quality before trusting it on an unfamiliar topic.
