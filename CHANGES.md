# J3P Advisor — build 2026-09-24-i

`app.py`, the pre-deploy checks, and `patch_exports.py` (unchanged from
`-h` — run it once if you have not already).

---

## Everything for a client is now on Add Client

Your screenshot caught the thing that gave it away: the confirmation said
"issue participant links from the Advisors tab" — a tab where the engagement
no longer appears. I moved the engagements and left the instructions behind.

Both pointers are gone, and the one genuinely missing piece is now here too.

| | Where it was | Where it is |
|---|---|---|
| Create the engagement | Add Client | Add Client |
| Read their website | Add Client | Add Client |
| Branding, colors, logo | Add Client | Add Client |
| Persona and referral address | Add Client | Add Client |
| Participant links | Add Client | Add Client |
| Photo | Add Client | Add Client |
| **Their documents** | **Knowledge tab** | **Add Client** |

## Their documents, where the advisor is not a choice

The Knowledge tab can still upload for any advisor — that is right for your
own coaches. But doing it there for a client means remembering to pick them
from a dropdown of everyone, and that is the step that gets missed. The
consequence is not cosmetic: a client's material answering another client's
questions.

Inside their engagement, the advisor is fixed. The form shows what they
already have, and says plainly that the shared base still applies on top:

> Retrieved only for Roy Herbst's sessions. The shared J3P base is still
> available to them on top of this — these are the documents nobody else
> can see.

Uploading returns you to Add Client rather than dropping you on Knowledge,
using the same whitelisted `return_to` pattern as the other forms.

## Verified

Rendered the tab with an engagement present and confirmed all nine pieces
are there, and that no text on the tab sends you to another one.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-i`.
