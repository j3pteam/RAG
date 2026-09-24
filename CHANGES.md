# J3P Advisor — build 2026-09-24-f

`app.py`, the pre-deploy checks, `verify_brand.py`, `brands/`, and the
deployment guides.

---

## Start from their website

**Add Client → Start from their website.** Type the organization and their
web address, press Read their site, and the form below fills in with what it
found: their name, their header color, and their logo.

It reads only what a site publishes **for exactly this purpose** — the
`og:image`, `apple-touch-icon`, `icon` and `theme-color` tags it already
hands to Slack, iMessage and search engines. No CSS is parsed and no colors
are sampled from images: a confident wrong color is worse than an empty
field someone fills in themselves.

## Nothing is applied silently

What it found is shown for review, with the logo previewed **on the header
color it would actually sit on** — and a line asking you to check it is the
mark and not a cropped social banner, which is what `og:image` often is.

Nothing is saved until you press Create the engagement. If the site
published nothing usable it says so plainly rather than leaving fields
mysteriously blank:

> They do not publish a theme color, so the header color is left as it is.
> No usable logo was published on that page. Upload one instead.

A file you choose yourself always beats the fetched one.

## The part that needed care

This route makes the server fetch a URL an admin types, which is a way to
reach anything the server can reach — the cloud metadata endpoint, the
database, another service on the private network. A typo would do it as
easily as malice.

Every address is resolved and checked **before** the request is made, and
refused if it lands anywhere private:

| Address | Result |
|---|---|
| `dartmouth.edu` | allowed |
| `http://169.254.169.254/latest/meta-data/` | refused |
| `http://127.0.0.1/admin` | refused |
| `http://10.0.0.5` | refused |
| `http://[::1]/` | refused |
| `file:///etc/passwd` | refused |
| `postgres://db.railway.internal:5432` | refused |

The same check runs again on the image URL, because a page can point its
logo anywhere. Responses are capped at 1 MB of HTML and 2 MB of image, with
an eight-second timeout.

The fetched logo is held in your session only until you create the
engagement or discard it. Keeping a copy of someone's logo before anyone has
agreed to use it serves nothing.

## Worth saying once

A logo being fetchable is not permission to use it. The form says so where
you will see it, and for a client like a cancer center their communications
office will have a view. This makes the setup quick; it does not make the
use authorized.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-f`.
