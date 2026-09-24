#!/usr/bin/env python3
"""Apply the internal-export fixes to exports.py.

Run once, from the repo root:

    python3 patch_exports.py

It edits exports.py in place and writes exports.py.bak first. Each edit is
matched exactly and the script refuses to write anything if any of them does
not match, so a half-applied file is not a possible outcome.
"""
import io
import os
import shutil
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "exports.py"

EDITS = [
    # 1. A replacement that reads, instead of a hole in the sentence.
    ('_BRAND_RE = re.compile("|".join(_BRAND_TOKENS), re.IGNORECASE)',
     '_BRAND_RE = re.compile("|".join(_BRAND_TOKENS), re.IGNORECASE)\n'
     '\n'
     '# What a removed name becomes mid-sentence. Deleting it outright produced\n'
     '# "priority access to \'s full practice and methodology" — visibly broken,\n'
     '# and the client sees it rather than the person who generated the file.\n'
     '_BRAND_REPLACEMENT = "our practice"',
     "brand replacement text"),

    # 2. Replace rather than delete; judge the drop on what deletion leaves.
    ('        # A short line that is essentially just branding gets dropped\n'
     '        residue = _BRAND_RE.sub("", line)\n'
     '        if len(re.sub(r"[^A-Za-z0-9]", "", residue)) < 12:\n'
     '            continue',
     '        # A line that is essentially nothing but branding is dropped.\n'
     '        # Judged on what would be left if the name were deleted, so the\n'
     '        # replacement cannot make an empty line look substantial.\n'
     '        if len(re.sub(r"[^A-Za-z0-9]", "", _BRAND_RE.sub("", line))) < 12:\n'
     '            continue\n'
     '        residue = _BRAND_RE.sub(_BRAND_REPLACEMENT, line)',
     "scrub replaces instead of deleting"),

    # 3. Splitting must not decide the scrubbing question for the caller.
    ('    body = scrub_brand(strip_meta(text or ""))',
     '    # Splitting only needs the boundaries. Scrubbing here would settle\n'
     '    # the question before the caller has had a say in it.\n'
     '    body = strip_meta(text or "")',
     "split_documents stops scrubbing"),

    # 4. The caller decides, because only the caller knows whose session it is.
    ('def build(fmt: str, text: str, title: str = None):\n'
     '    """Return (BytesIO, filename, mimetype) for the requested format."""\n'
     '    fmt = (fmt or "").lower().strip()\n'
     '    if fmt not in BUILDERS:\n'
     '        raise ValueError(f"Unsupported format: {fmt}")\n'
     '    # Chat-only instructions and advisor branding must never reach the document\n'
     '    text = scrub_brand(strip_meta(text))',
     'def build(fmt: str, text: str, title: str = None, scrub: bool = True):\n'
     '    """Return (BytesIO, filename, mimetype) for the requested format.\n'
     '\n'
     '    scrub=False keeps the firm\'s own names in the document. That is\n'
     '    correct for an internal session, where those names are the subject\n'
     '    rather than a leak — the advisor is talking to colleagues about the\n'
     '    firm\'s own work. The caller decides, because only the caller knows\n'
     '    whose session this is.\n'
     '    """\n'
     '    fmt = (fmt or "").lower().strip()\n'
     '    if fmt not in BUILDERS:\n'
     '        raise ValueError(f"Unsupported format: {fmt}")\n'
     '    # Chat-only instructions never belong in a document, whoever it is for.\n'
     '    text = strip_meta(text)\n'
     '    if scrub:\n'
     '        text = scrub_brand(text)',
     "build takes a scrub flag"),
]


def main():
    if not os.path.isfile(PATH):
        print(f"  {PATH} not found. Run this from the repo root, or pass the path.")
        return 1

    src = io.open(PATH, encoding="utf-8").read()

    if "_BRAND_REPLACEMENT" in src:
        print("  Already patched — nothing to do.")
        return 0

    problems = []
    for old, _new, label in EDITS:
        n = src.count(old)
        if n != 1:
            problems.append(f"{label}: matched {n} times, expected 1")
    if problems:
        print("  Refusing to edit — this exports.py does not look like the one "
              "these changes were written against:\n")
        for p in problems:
            print("   - " + p)
        print("\n  Nothing was written. Send me the current file and I will "
              "redo the patch against it.")
        return 1

    for old, new, label in EDITS:
        src = src.replace(old, new)
        print(f"  ok  {label}")

    shutil.copy2(PATH, PATH + ".bak")
    io.open(PATH, "w", encoding="utf-8").write(src)

    import ast
    try:
        ast.parse(src)
    except SyntaxError as e:
        shutil.copy2(PATH + ".bak", PATH)
        print(f"\n  The result would not parse ({e}); {PATH} has been restored.")
        return 1

    print(f"\n  {PATH} patched. The original is at {PATH}.bak")
    return 0


if __name__ == "__main__":
    sys.exit(main())
