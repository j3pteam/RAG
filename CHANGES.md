# J3P Advisor — build 2026-09-23-a

`app.py`, the pre-deploy checks, `verify_brand.py`, `brands/`, and the
deployment guides.

---

## A client logo can be uploaded

**Advisors → the advisor → Client branding → Logo.** Choose a file, upload,
done. Stored in the database like the advisor photo, not referenced by URL.

A URL was the wrong default for this. A client's mark is rarely sitting on a
public URL you can hotlink, and a URL that moves later breaks the page
silently — nobody notices until a participant sees a broken image on a page
carrying their own institution's name. The bytes cannot move.

PNG, SVG, JPEG, WEBP or GIF, up to 2 MB. SVG is included deliberately: it is
the format a communications office hands over, and a logo in a header should
stay sharp.

| Upload | Result |
|---|---|
| 48 KB PNG | accepted |
| 12 KB SVG | accepted |
| 50 KB PDF | rejected — not an image type |
| empty file | rejected |
| 5 MB PNG | rejected, with the size named |

## The details that make it usable

- **The preview sits on the header color it will actually appear against**,
  not on white. A logo with a dark wordmark looks fine on a white card and
  disappears on a navy header, and finding that out after sending the link
  is the wrong order.
- **An upload beats the URL field**, and the URL field says so when one
  exists. Both can be set — someone pastes a URL, then uploads a file later
  — and the upload is both the more deliberate act and the one that cannot
  break.
- **Remove is separate** and restores this site's logo.
- The cache window matches the photo's, so a replaced logo appears within
  five minutes rather than needing a hard refresh.
- The "Delivered by J3P Health" line now also appears for an uploaded logo,
  which the previous check missed.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-23-a`.

For Dr. Herbst: upload Dartmouth's mark, set the header color to match, and
check the preview before sending any participant links.
