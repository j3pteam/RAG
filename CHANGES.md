# J3P Advisor — build 2026-09-24-b

`app.py`, the pre-deploy checks, `verify_brand.py`, `brands/`, and the
deployment guides.

---

## Example names are fictional now

```
Advisor name     e.g. John Sample, MD
Organization     e.g. Sample Health System
Consent record   e.g. Confirmed by email with Dr. Sample, 22 Sep 2026
```

I changed the organization example as well as the name. A form reading
"John Sample" next to "Dartmouth Cancer Center" is incoherent, and a real
prospect's name sitting in placeholder text is the sort of thing that ends
up in a screenshot shared with someone else.

## The blank word in your screenshot

The sentence read:

> an advisor named for a client but still wearing **'s** branding

`{{ org_short }}` was rendering empty. The admin template was given
`org_principal` but never `org_name` or `org_short`, so three strings across
the panel came out blank — that one, the line explaining that
"Delivered by *(blank)*" appears on client-branded pages, and the heading
"Persona of someone outside *(blank)*".

All three now read correctly:

> an advisor named for a client but still wearing **J3P's** branding and
> speaking as **Alan Friedman**

## A note on how that one got through

The render test exercises every tab, which is how the tab itself was
verified — but it supplies its own context, so it filled in values the real
route does not. A missing variable renders as empty in Jinja rather than
failing, so nothing broke; the sentence just quietly lost a word.

Your screenshot caught it. I have not found a way to check for it
automatically that does not amount to reimplementing the route inside the
test, so for now it stays a thing to notice.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-b`.
