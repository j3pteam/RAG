#!/usr/bin/env python3
"""Check that a brand file produces a complete rebrand.

A checklist tells you what you meant to set. This renders the actual
participant page against the brand file and reads what comes out, which is
the only way to find the string someone forgot — including one added to the
code next month that nobody remembered to make configurable.

    ./verify_brand.py brands/meridian.env

Exit code is 0 only if nothing from the previous brand shows through.
"""
import os
import re
import sys

REQUIRED = ["ORG_NAME", "ORG_SHORT", "ORG_LEGAL_NAME", "ORG_PRINCIPAL",
            "PERSONA_NAME", "CONTACT_EMAIL", "FLASK_SECRET_KEY"]

# Terms that must not survive a rebrand. Extend this when the house brand
# gains a name — an unlisted term is one this check cannot catch.
PREVIOUS_BRAND = ["J3P", "j3p", "Residency Select", "J3 Personica",
                  "J3Personica", "Alan Friedman", "j3p.health"]

# Identifiers and storage keys, not visible text. Excluded by exact token so
# that "J3PSpeech" passes while a stray "J3P Advisor" does not.
NOT_VISIBLE = ["J3PSpeech", "j3p_autospeak", "j3p_voice", "j3p_rate",
               "j3p_hist_open", "j3p_context_done", "j3p_personality",
               "j3p_ack", "j3p_seen"]


def read_env(path):
    values = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    return values


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    values = read_env(path)

    problems = []
    for key in REQUIRED:
        if not values.get(key):
            problems.append(f"{key} is empty — it is required")

    if "ORG_NAMING_RULES" not in values:
        problems.append("ORG_NAMING_RULES is missing entirely. Set it to an "
                        "empty value if this organization has no confusable "
                        "entity names — an empty value is a real answer, a "
                        "missing line means the previous brand's rules apply")

    if problems:
        print(f"  {len(problems)} problem(s) in {path}:\n")
        for p in problems:
            print("   - " + p)
        return 1

    # Render the participant page exactly as the app would.
    # Empty values are set too. ORG_NAMING_RULES="" is a deliberate answer
    # meaning "this firm has no confusable names"; skipping it would leave
    # the previous brand's rules in force and the check would pass anyway.
    for k, v in values.items():
        os.environ[k] = v
    os.environ.setdefault("DATABASE_URL", "")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    src = open("app.py", encoding="utf-8").read()

    # Pull the pieces the page is built from without importing the app,
    # which would try to reach a database.
    from jinja2 import Environment
    ns = {"os": os}
    block = src[src.index("ORG_NAME = os.environ.get"):src.index("\n\nCONFIG = {")]
    exec(block, ns)
    brand = ns["brand"]

    template = re.search(r'^INDEX_HTML = r?"""(.*?)"""\n', src, re.S | re.M).group(1)
    release = re.search(r'^RELEASE_BODY_HTML = """(.*?)"""', src, re.S | re.M).group(1)

    page = Environment().from_string(template).render(
        cfg={"persona_name": ns["PRODUCT_NAME"],
             "opening": brand("Hello, welcome to your session with the {product}."),
             "placeholder": values.get("PERSONA_PLACEHOLDER") or "How can I help you?",
             "favicon_url": values.get("BRAND_FAVICON_URL", ""),
             "logo_url": values.get("BRAND_LOGO_URL", ""),
             "avatar_url": values.get("ADVISOR_AVATAR_URL", ""),
             "avatar_loop_url": "", "avatar_name": ns["PRODUCT_NAME"],
             "navy": values.get("BRAND_NAVY", "#27334A"),
             "gold": values.get("BRAND_GOLD", "#D2BC8D"),
             "paper": values.get("BRAND_PAPER", "#FAF6F0"),
             "footer_disclaimer": values.get("FOOTER_DISCLAIMER")
                 or "For informational purposes only. Not official advice.",
             "footer_ai_note": brand("The {product} is AI and can make mistakes. "
                                     "Please double-check responses."),
             "footer_cta_label": values.get("FOOTER_CTA_LABEL") or "Schedule",
             "footer_cta_url": values.get("FOOTER_CTA_URL", ""),
             "max_upload_mb": 100, "max_image_mb": 5,
             "talking_avatar": "off",
             "contact_email": values["CONTACT_EMAIL"]},
        show_avatar=True, advisor_photo_override=False, avatar_no_photo=True,
        allow_materials=True, show_scheduling_button=True,
        release_heading="Release & Acknowledgment",
        release_body=brand(release), release_checkbox_label="I agree",
        personality_questions=[], personality_enabled=False,
        context_intake_enabled=False, avatar_version=1, internal_only=False,
        page_advisor_slug="", page_voice_mode="auto",
        org_name=ns["ORG_NAME"], org_short=ns["ORG_SHORT"],
        context_position_options=[], context_specialization_options=[])

    # Also check the system prompt, which the participant never sees but the
    # advisor speaks from — a missed name there is worse, not better.
    prompt_start = src.index('"1. IDENTITY. You are the {product}')
    prompt = brand(src[prompt_start:prompt_start + 6000])

    findings = []
    for surface, text in (("the participant page", page), ("the system prompt", prompt)):
        cleaned = text
        for token in NOT_VISIBLE:
            cleaned = cleaned.replace(token, "")
        for term in PREVIOUS_BRAND:
            for m in re.finditer(re.escape(term), cleaned):
                snippet = cleaned[max(0, m.start() - 55):m.start() + 55]
                snippet = re.sub(r"\s+", " ", snippet).strip()
                findings.append((surface, term, snippet))

    if findings:
        print(f"  {len(findings)} place(s) where the previous brand still shows:\n")
        seen = set()
        for surface, term, snippet in findings:
            key = (surface, snippet)
            if key in seen:
                continue
            seen.add(key)
            print(f"   [{surface}] {term}")
            print(f"      …{snippet}…\n")
        return 1

    print(f"  {values['ORG_NAME']} — clean.")
    print(f"     product:   {ns['PRODUCT_NAME']}")
    print(f"     entity:    {ns['ORG_LEGAL_NAME']}")
    print(f"     principal: {ns['ORG_PRINCIPAL']}")
    print(f"     contact:   {values['CONTACT_EMAIL']}")
    print("\n     No trace of the previous brand on the participant page or "
          "in the system prompt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
