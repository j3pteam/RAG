#!/usr/bin/env python3
"""
Tenant configuration — everything that makes this deployment one client's
advisor rather than another's.

WHY THIS EXISTS
    The application is one codebase serving one client per deployment. All
    the parts that differ between clients — the organisation's name, its
    brand colours, its staff, its legal entity, the subject matter the
    advisor is allowed to discuss, the brand names it must never print —
    were spread across the system prompts, the scrubbers, the templates and
    the stylesheet. Standing up a second client meant hunting through
    ~19,000 lines and hoping nothing was missed. This puts every one of
    those values in a single file per client.

WHAT IT DELIBERATELY DOES NOT DO
    It does not make the app multi-tenant. One deployment serves one client,
    with its own database and its own environment. That is a decision, not
    an omission: this application stores coaching transcripts, personality
    self-reports, 360 feedback and biometric exports. Partitioning that by a
    tenant_id column across ~20 tables means every future query is one
    forgotten WHERE clause away from showing one client another client's
    participants. Separate deployments make that failure impossible rather
    than unlikely. The cost is a second Railway project per client, which is
    a smaller price than the failure it removes.

HOW IT LOADS
    TENANT=<slug> selects tenants/<slug>.json. Anything the file omits falls
    back to the built-in defaults below, which are J3P's, so an incomplete
    or missing file degrades to the current behaviour instead of booting a
    half-branded app. A malformed file is logged and ignored for the same
    reason.

ADDING A CLIENT
    See WHITE_LABEL.md. Short version: copy tenants/example.json, fill it
    in, add the brand image files, set TENANT and the usual secrets on a new
    deployment with its own database.
"""
import json
import os
import re
from pathlib import Path

TENANT_SLUG = os.environ.get("TENANT", "j3p").strip().lower()
TENANT_DIR = Path(os.environ.get("TENANT_DIR", "tenants"))


# ---------------------------------------------------------------------------
# Defaults — J3P's own values, so an absent config file changes nothing.
# ---------------------------------------------------------------------------
DEFAULTS = {
    # --- Identity -----------------------------------------------------------
    "slug": "j3p",
    "org_name": "J3P Health",
    "org_short": "J3P",
    "legal_entity": "Residency Select LLC dba J3P Health",
    "contact_email": "clientservices@j3p.health",
    "alert_email": "afriedman@j3p.health",

    # --- The advisor persona ------------------------------------------------
    "persona_name": "J3P Advisor",
    "persona_opening": "Hello, welcome to your session with the J3P Advisor.",
    "persona_placeholder": "How can I help you?",

    # --- Brand --------------------------------------------------------------
    "brand": {
        "navy": "#27334A",      # primary / bold surfaces and text
        "gold": "#D2BC8D",      # accent, selected states
        "paper": "#FAF6F0",     # page background
        "rust": "#9D432C",      # destructive / danger
        "font": "Jost",         # brand face, loaded from Google Fonts
        "font_weights": "300;400;500;600",
    },
    "assets": {
        "logo_url": "/full_logo.png",
        "favicon_url": "/monogram.jpg",
        "avatar_url": "/advisor_avatar.jpg",
        "avatar_loop_url": "/advisor_idle.mp4",
    },

    # --- What the advisor is for -------------------------------------------
    # Dropped verbatim into the scope guard. This is the single most
    # important field to get right for a new client: it is what the model
    # uses to decide whether a question is in scope at all.
    "expertise": (
        "leadership development, organizational behavior, behavioral assessment, "
        "physician/healthcare leadership, team dynamics, executive coaching, "
        "communication, self-awareness, negotiation, career navigation, "
        "and related professional development topics within healthcare and "
        "high-stakes organizational settings"
    ),
    # How participants are described when the advisor has no specifics. J3P's
    # audience is physician leaders; another client's might be "school
    # principals" or "partners at the firm".
    "audience": "physician leaders",

    # --- Names the advisor must never print --------------------------------
    # Legacy or internal brands. Each is (forbidden, replacement).
    "forbidden_names": [
        ["J3P Healthcare Solutions", "J3P"],
        ["J3P Healthcare", "J3P"],
        ["J3Personica", "the assessment framework"],
        ["J3 Personica", "the assessment framework"],
        ["Residency Select", "the residency selection tool"],
    ],

    # --- Staff, for the contact scrubber -----------------------------------
    # Any passage naming one of these people alongside contact language is
    # a referral to an individual and gets replaced with client services.
    # first/last lets the scrubber match "Alan", "Alan Friedman", "Dr.
    # Friedman" and "Friedman" without a hand-written regex per client.
    "staff": [
        {"first": "Alan", "last": "Friedman"},
        {"first": "Ivy", "last": "Seader"},
        {"first": "Diane", "last": "Blake"},
    ],
    # Email domains and local-parts that identify an internal address.
    "internal_domains": ["j3p.health", "j3phealth.com",
                         "j3personica.com", "residencyselect.com"],
    "staff_email_locals": ["afriedman", "alanfriedman", "alan.friedman",
                           "iseader", "ivy.seader", "ivyseader",
                           "dblake", "diane.blake", "dianeblake"],

    # --- Scheduling ---------------------------------------------------------
    "scheduling_url": ("https://app.acuityscheduling.com/catalog.php"
                       "?owner=29987697&action=addCart&clear=1&id=2262965"),
    "scheduling_label": "Schedule Time With a J3P Advisor",
    "scheduling_cta_text": "To schedule time with a J3P Advisor, please",

    # --- Footer and legal ---------------------------------------------------
    "footer_disclaimer": "For informational purposes only. Not official advice.",
    "footer_ai_note": ("The J3P Advisor is AI and can make mistakes. "
                       "Please double-check responses."),
    # {legal_entity} and {persona_name} are substituted in.
    "release_body": """
  <p>
    By checking the box below, I acknowledge that I am voluntarily using
    the {persona_name} and understand that the content, coaching and guidance
    provided are for personal and professional development purposes only.
    I understand that these activities are not medical, psychological,
    legal, or other professional advice, and I am responsible for my own
    decisions and actions.
  </p>
  <p>
    To the extent permitted by law, I release {legal_entity}, its coaches,
    employees, and representatives from liability arising from my voluntary
    use of the {persona_name}.
  </p>
""",
}


def _deep_merge(base: dict, over: dict) -> dict:
    """Overlay one level of nesting, so a config can set a single brand
    colour without having to restate the whole block."""
    out = dict(base)
    for key, val in (over or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **val}
        else:
            out[key] = val
    return out


def _load() -> dict:
    path = TENANT_DIR / f"{TENANT_SLUG}.json"
    if not path.exists():
        # Not an error: the default tenant runs without a file at all.
        return dict(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as fh:
            return _deep_merge(DEFAULTS, json.load(fh))
    except Exception as e:
        # A broken config must not take the deployment down — serving the
        # default branding is recoverable; failing to boot is not.
        print(f"[tenant] could not read {path}: {e} — using defaults", flush=True)
        return dict(DEFAULTS)


TENANT = _load()


# ---------------------------------------------------------------------------
# Derived values. Built once here so no caller has to assemble them, and so
# a client that forgets a field still gets something coherent.
# ---------------------------------------------------------------------------

def release_body_html() -> str:
    return TENANT["release_body"].format(
        legal_entity=TENANT["legal_entity"],
        persona_name=TENANT["persona_name"],
        org_name=TENANT["org_name"],
    )


def staff_name_pattern() -> str:
    """Regex alternation matching any staff member by first name, full name,
    honorific plus surname, or surname alone — built from the staff list so
    a new client never hand-writes this."""
    parts = []
    for person in TENANT["staff"]:
        first = re.escape((person.get("first") or "").strip())
        last = re.escape((person.get("last") or "").strip())
        if first and last:
            parts.append(rf"{first}(?:\s+{last})?")
            parts.append(rf"(?:Mr|Ms|Mrs|Dr)\.?\s+{last}")
            parts.append(last)
        elif first:
            parts.append(first)
        elif last:
            parts.append(last)
    if not parts:
        # No staff configured: a pattern that can never match, rather than
        # an empty alternation that matches everything.
        return r"(?!x)x"
    return r"\b(?:" + "|".join(parts) + r")\b"


def is_configured() -> bool:
    """True when this deployment is running a real tenant file rather than
    falling back to the defaults. Surfaced at /health."""
    return (TENANT_DIR / f"{TENANT_SLUG}.json").exists()


def summary() -> dict:
    """Non-secret description of the active tenant, for /health."""
    return {
        "tenant": TENANT_SLUG,
        "org_name": TENANT["org_name"],
        "persona_name": TENANT["persona_name"],
        "config_file_present": is_configured(),
        "staff_configured": len(TENANT["staff"]),
        "forbidden_names": len(TENANT["forbidden_names"]),
    }
