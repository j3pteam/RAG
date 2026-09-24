# J3P Advisor — build 2026-09-24-l

`app.py`, the pre-deploy checks, and `patch_exports.py` (unchanged).

---

## Copy and Share on the session link

The engagement's session link was plain text you had to select by hand. It
is now a clickable link with **Copy** and **Share** beside it, matching the
participant links directly below.

Share uses the phone's own share sheet where there is one, and falls back to
a small menu on desktop. The message names the advisor:

> Here is your private link to a session with Roy Friedman:
> …
> It opens in a browser — nothing to install.

## A Copy button that has never worked

While wiring this I found that the Copy button on the **internal advisor**
card uses `data-copy`. The handler reads `data-url`. It has done nothing at
all since I added it in `2026-09-22-a` — clicking it silently copied
nothing.

Fixed, and given a Share button too. There are no `data-copy` attributes
left in the file.

That one is on me twice over: I wrote the attribute without checking the
handler, and a button that silently does nothing is the hardest kind of
failure for you to report — it looks like the clipboard not working.

## And a brand leak in the share text

The share message fell back to a hardcoded "the J3P Advisor" when no advisor
name was attached. On a white-label deployment that would have mailed a
client's own people an invitation to J3P. It now uses whatever
`PERSONA_NAME` is set to for that deployment.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-l`.
