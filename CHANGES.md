# J3P Advisor — build 2026-09-24-n

`app.py`, the pre-deploy checks, and `patch_exports.py` (unchanged).

---

## I cannot tell from here why the branding did not take — so the panel now says

Your screenshot shows a **broken image** where the logo should be and the
colors unchanged. Those are two different failures and I could not tell
which from outside, so rather than guess a third time I made the panel
report what is actually stored.

Each engagement now shows:

```
Logo: uploaded          Header: ■ #00693E      Accent: ■ #9D162E
Logo: from a URL        Header: not set        Accent: not set
Logo: not set           Header: not set        Accent: not set
   — using this site's
```

**"not set" and "set to something that looks like the default" are
indistinguishable on the session page.** That is why this kept being hard to
diagnose. Open Add Client after deploying and the row will say which case
you are in.

If it reads **from a URL**, the card also warns that many sites block other
sites from loading their images — which is exactly what a broken image in
the header looks like — and suggests uploading the file instead.

## A broken image no longer reaches a client's session

If a client logo fails to load for any reason, the header falls back to this
deployment's logo. A broken-image icon in the header of a client's own
session is the worst possible place to discover a bad URL.

## And a bug in that fix, caught before it shipped

My first version produced:

```html
onerror="this.onerror=null; this.src="/full_logo.png";"
```

`|tojson` emits double quotes, which closed the attribute early and broke
the tag. The HTML check does not look inside attribute values, so it passed
— I caught it by parsing the rendered tag and checking the attribute
survived intact. Now single-quoted, and verified to parse as one attribute
with its value whole.

---

## Installing

Replace `app.py`, keep the scripts and `brands/` alongside. Diagnostics
should report `2026-09-24-n`.

Then open Add Client and read the Logo / Header / Accent row on Roy Herbst.
Tell me what it says and I will know which of the two failures this is.
