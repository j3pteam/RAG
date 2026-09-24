# J3P Advisor — build 2026-09-23-b

`app.py`, the pre-deploy checks, `verify_brand.py`, `brands/`, and the
deployment guides.

---

## First, what I did not build

A guarantee that no reply ever matches what another model would say is not
achievable, and I would rather say so than ship something that appears to do
it.

**The app is built on Claude.** Its replies are a Claude model's output,
shaped by your prompt and your knowledge base. There is no version of this
where its answers are not, at root, one model's answers.

**Checking is impossible in principle.** It would mean querying every model,
for every question, before every reply — and they change weekly. Nothing can
return an answer that is guaranteed different from something it never saw.

**Succeeding would make the advisor worse.** Asked what the TIPI measures,
there is one correct answer. Forcing a different one means being wrong on
purpose, in front of physician leaders who will notice.

## What the request is actually about

A participant should never feel they could have gotten this from ChatGPT.
That is a real goal, and mostly already handled: the prompt has nine
differentiation rules, including one stating the advisor is not ChatGPT,
Claude, Gemini or Copilot and must not name an underlying model.

The gap was that nothing required the **substance** to be specific — only
the voice. A reply could obey every tone rule and still be generic advice
in a distinctive style.

## Rule 4b: say something only this practice could say

Added to the prompt, applying to every response:

- Anchor in the retrieved material, this practice's frameworks, or what the
  person has already said — their role, their organization, the constraint
  they named, the pattern in their assessment
- Where the retrieved material takes a position, take it, **including where
  it cuts against conventional advice** — this is the one thing a general
  assistant structurally cannot do
- No numbered lists of universal best practices
- If the honest answer really is generic, say it in one sentence and spend
  the reply on what is specific to them
- Never "research shows" in the abstract when specific material is available

## And a way to see whether it is working

The grounding check already re-runs retrieval against every reply. I have
reframed what it measures in Diagnostics, because it is the closest thing
you have to a distinctiveness meter:

> An unsupported reply is one the model produced from its own general
> knowledge — which means a participant could have gotten much the same
> answer from any general-purpose assistant.

**A rising unsupported count means the knowledge base is thin on what people
are actually asking about.** That is the real lever. Prompt wording changes
the voice; only your material changes what the advisor knows that others do
not — and that is the part no one else can copy.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-23-b`.

Worth watching after a week of real use: Diagnostics → Answer grounding. The
questions landing in the unsupported bucket are your content roadmap.
