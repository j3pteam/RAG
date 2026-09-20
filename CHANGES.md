# J3P Advisor — build 2026-09-20-h

`app.py`, plus the pre-deploy checks. Includes everything from `-g`.

---

## Why none of my previous stop fixes could work

`new Audio(url)` creates an element that is **never inserted into the
document**. So the sweep I added in `-e` —
`document.querySelectorAll("audio")` — was reaching nothing at all. It found
no cloned-voice player because there was never one in the page to find.

That left exactly one handle: a property on the message element. And "New
conversation" removes those elements, so after clearing the chat there was
no way for anything on the page to stop the audio. It simply played on.

I shipped that sweep as a fix. It was not one, and I should have checked
what it actually selected instead of assuming.

## The fix

Every cloned-voice player is now registered in a plain set held in the
page's own scope, independent of the DOM entirely. It is added when
playback starts and dropped when it ends. Stopping iterates that set.

That works whether or not the message is still on screen, which is the case
the previous attempts all missed.

**And New conversation now stops speech**, which it never did — clearing the
transcript left the reply being read aloud over an empty page.

Verified four ways: a player stops while its message is on the page; a
player stops after the message element is gone; two queued players both
stop; and a finished player that has already been dropped is not touched
again.

---

## From -g and -f

The avatar status reads plain `Speaking` with no voice detail. Markdown
tables render as tables rather than raw pipes.

---

## Installing

Replace `app.py`, commit to `main`. Diagnostics should report version
`2026-09-20-h`.

The status label in your screenshot still read "SPEAKING (THEIR OWN VOICE)",
which was removed in `-g` — so the build you tested was older than that. It
is worth confirming Diagnostics shows `2026-09-20-h` before judging this
one.
