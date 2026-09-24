# J3P Advisor — build 2026-09-24-m

`app.py`, the pre-deploy checks, and `patch_exports.py` (unchanged).

---

## Saving a client setting keeps you on Add Client

Setting Roy Herbst's branding dropped you on the **Advisors** tab — a tab
his engagement is not on. The three routes behind those forms were written
when the forms sat on the advisor card, and still sent people to Advisors
afterward.

**18 redirects across three routes** now return to Add Client: branding,
persona, and logo — including every validation failure, so a rejected color
leaves you on the form you were filling in rather than somewhere else
entirely.

## I stopped fixing these one report at a time

This is the fourth build in a row correcting something left behind by moving
client engagements to their own tab. Rather than wait for the next one, I
audited it:

**Every client-related route, and where it sends you:**

```
/admin/clients/lookup             clients
/admin/clients/lookup/clear       clients
/admin/clients/create             clients
/admin/advisors/logo/<slug>       clients
/admin/advisors/persona/<slug>    clients
/admin/advisors/branding/<slug>   clients
```

**And the Advisors pane itself** — no branding form, no persona form, no
client logo upload, no color fields, and the filter that keeps engagements
out of the list is in place.

That is all of it. If something client-related still appears on Advisors
after this, it is something I have not thought of rather than something I
knew about and missed.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-m`.
