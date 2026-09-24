# J3P Advisor — build 2026-09-24-j

`app.py`, the pre-deploy checks, and `patch_exports.py` (unchanged — run it
once if you have not already).

---

## Links for a client are created, and stay, on Add Client

The link form inside an engagement was still posting `return_to=advisors`,
so creating one threw you onto the Advisors tab — where the engagement does
not appear. The shared form now returns to whichever tab it was used on.

## Client engagements are gone from the other tabs' pickers

They were still reachable in two places I had missed:

**Voice sample → Copy to…** on the Advisors tab listed client engagements as
a destination. A client engagement is not a person with a voice to clone,
and copying a coach's voice onto one would mean a real person speaking as a
client's advisor.

**Knowledge → the four "scoped to…" pickers** on upload, folder upload, URL
and text. Choosing a client there means picking them from a dropdown of
everyone, which is the step that gets missed — and the consequence is a
client's material answering another client's questions. Their documents are
uploaded inside their engagement, where the advisor is fixed rather than
chosen.

| | Advisors | Knowledge | Add Client |
|---|---|---|---|
| Client offered in a picker | 0 | 0 in upload | — |
| Client's links, docs, branding | no | no | yes |

## One thing I deliberately did not remove

The **reassignment controls on documents that already exist** — the checkbox
list and the per-row scope selector — still list client engagements. Two of
them, confirmed in the render.

Removing them would have been more consistent and worse: a document already
assigned to a client could then never be unassigned or moved, with no way
back. Consistency is not worth stranding data.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-j`.
