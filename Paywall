"""
Paywall module: email magic-link authentication + Stripe subscription gating.

Configuration via env vars:
    PAYWALL_ENABLED           "true" | "false"  (default: "false" — turn on when ready)
    STRIPE_SECRET_KEY         sk_live_... or sk_test_...
    STRIPE_PRICE_ID           price_...   (the monthly subscription price)
    STRIPE_WEBHOOK_SECRET     whsec_...   (from Stripe webhook endpoint)
    POSTMARK_SERVER_TOKEN     for sending magic-link emails
    FROM_EMAIL                sender address (default: noreply@j3phealth.com)
    FROM_NAME                 sender name (default: "J3P Advisor")
    PUBLIC_BASE_URL           e.g. https://web-production-901d85.up.railway.app
    PAYWALL_WHITELIST         comma-separated emails that skip payment entirely
    MAGIC_LINK_TTL_MINUTES    how long magic links stay valid (default 30)
    FLASK_SECRET_KEY          used for signing tokens (same one Flask uses)

Database: adds a `paywall_users` table via ensure_schema().
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

from flask import request, redirect, url_for, session, render_template_string, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

import database as db


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def _env_bool(name: str, default: bool = False) -> bool:
    return (os.environ.get(name, "true" if default else "false") or "").strip().lower() in ("1", "true", "yes", "on")


PAYWALL_ENABLED = _env_bool("PAYWALL_ENABLED", False)
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
POSTMARK_SERVER_TOKEN = os.environ.get("POSTMARK_SERVER_TOKEN", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@j3phealth.com")
FROM_NAME = os.environ.get("FROM_NAME", "J3P Advisor")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
WHITELIST = {
    e.strip().lower() for e in (os.environ.get("PAYWALL_WHITELIST", "") or "").split(",") if e.strip()
}
MAGIC_LINK_TTL_MINUTES = int(os.environ.get("MAGIC_LINK_TTL_MINUTES", "30"))
_SECRET = os.environ.get("FLASK_SECRET_KEY", "change-me")

_serializer = URLSafeTimedSerializer(_SECRET, salt="magic-link-v1")


def is_configured() -> bool:
    """Paywall is 'configured' if Stripe keys + Postmark token + base URL are all set.
    If PAYWALL_ENABLED is true but config is incomplete, the app runs in the pre-paywall
    mode with a warning logged rather than breaking."""
    return bool(STRIPE_SECRET_KEY and STRIPE_PRICE_ID and POSTMARK_SERVER_TOKEN and PUBLIC_BASE_URL)


def is_active() -> bool:
    """True when the paywall should actually gate requests."""
    return PAYWALL_ENABLED and is_configured()


# ---------------------------------------------------------------------------
# Database schema
# ---------------------------------------------------------------------------
def ensure_schema():
    """Create the paywall_users table if it doesn't exist."""
    if not db.is_enabled():
        return
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS paywall_users (
                    email TEXT PRIMARY KEY,
                    stripe_customer_id TEXT,
                    subscription_status TEXT DEFAULT 'inactive',
                    subscription_current_period_end TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()


def _get_user(email: str) -> Optional[dict]:
    if not db.is_enabled():
        return None
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM paywall_users WHERE email = %s;", (email.lower(),))
            return cur.fetchone()


def _upsert_user(email: str, **fields) -> None:
    if not db.is_enabled():
        return
    email = email.lower()
    cols = ["email"] + list(fields.keys()) + ["updated_at"]
    values = [email] + list(fields.values()) + [datetime.utcnow()]
    placeholders = ", ".join(["%s"] * len(values))
    update_clause = ", ".join([f"{k} = EXCLUDED.{k}" for k in fields.keys()] + ["updated_at = EXCLUDED.updated_at"])
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO paywall_users ({', '.join(cols)})
                VALUES ({placeholders})
                ON CONFLICT (email) DO UPDATE SET {update_clause};
                """,
                values,
            )
        conn.commit()


def is_user_subscribed(email: str) -> bool:
    """Whitelist bypass, then DB check for active subscription."""
    if not email:
        return False
    email = email.lower()
    if email in WHITELIST:
        return True
    user = _get_user(email)
    if not user:
        return False
    status = (user.get("subscription_status") or "").lower()
    # 'trialing' also counts as active; 'past_due' does not
    if status not in ("active", "trialing"):
        return False
    # If we have an end date, confirm it hasn't lapsed
    end = user.get("subscription_current_period_end")
    if end and end < datetime.utcnow():
        return False
    return True


# ---------------------------------------------------------------------------
# Magic-link email delivery via Postmark
# ---------------------------------------------------------------------------
def send_magic_link_email(to_email: str, magic_url: str) -> bool:
    """Send the magic-link email. Returns True on success, False on failure."""
    if not POSTMARK_SERVER_TOKEN:
        return False
    body_text = (
        f"Hi,\n\n"
        f"Click the link below to sign in to the J3P Advisor. "
        f"This link expires in {MAGIC_LINK_TTL_MINUTES} minutes.\n\n"
        f"{magic_url}\n\n"
        f"If you didn't request this, you can ignore this email.\n\n"
        f"— J3P Advisor"
    )
    body_html = (
        f"<p>Hi,</p>"
        f"<p>Click the link below to sign in to the J3P Advisor. "
        f"This link expires in {MAGIC_LINK_TTL_MINUTES} minutes.</p>"
        f'<p><a href="{magic_url}" style="display:inline-block;padding:12px 24px;'
        f'background:#27334A;color:#D2BC8D;text-decoration:none;border-radius:2px;'
        f'font-family:sans-serif;letter-spacing:0.1em;">Sign in to J3P Advisor</a></p>'
        f'<p style="color:#666;font-size:0.85em;">Or paste this URL into your browser:<br />'
        f'<a href="{magic_url}">{magic_url}</a></p>'
        f'<p style="color:#666;font-size:0.85em;">If you didn\'t request this, you can ignore this email.</p>'
    )
    payload = {
        "From": f"{FROM_NAME} <{FROM_EMAIL}>",
        "To": to_email,
        "Subject": "Your J3P Advisor sign-in link",
        "TextBody": body_text,
        "HtmlBody": body_html,
        "MessageStream": "outbound",
    }
    req = urllib.request.Request(
        "https://api.postmarkapp.com/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": POSTMARK_SERVER_TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        print(f"[paywall] Postmark send failed: {e.code} {body}")
        return False
    except Exception as e:
        print(f"[paywall] Postmark send exception: {e}")
        return False


# ---------------------------------------------------------------------------
# Magic-link tokens
# ---------------------------------------------------------------------------
def make_magic_link(email: str, base_url: str) -> str:
    token = _serializer.dumps(email.lower())
    return f"{base_url.rstrip('/')}/auth/verify?token={token}"


def verify_magic_link(token: str) -> Optional[str]:
    """Return the email if token is valid + unexpired, else None."""
    try:
        email = _serializer.loads(token, max_age=MAGIC_LINK_TTL_MINUTES * 60)
        return email.lower()
    except SignatureExpired:
        return None
    except BadSignature:
        return None


# ---------------------------------------------------------------------------
# Access gate decorator
# ---------------------------------------------------------------------------
def paywall_required(f):
    """Route decorator: requires authenticated + subscribed user.
    If paywall is disabled or misconfigured, is a no-op."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not is_active():
            return f(*args, **kwargs)
        email = session.get("authenticated_email")
        if not email:
            # AJAX request needs JSON; page request needs redirect
            if request.path == "/chat":
                return jsonify({"error": "not_authenticated", "redirect": "/auth/login"}), 401
            return redirect(url_for("auth_login"))
        if not is_user_subscribed(email):
            if request.path == "/chat":
                return jsonify({"error": "not_subscribed", "redirect": "/billing/checkout"}), 402
            return redirect(url_for("billing_checkout"))
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Stripe helpers
# ---------------------------------------------------------------------------
_stripe = None


def _get_stripe():
    global _stripe
    if _stripe is None:
        import stripe as stripe_lib
        stripe_lib.api_key = STRIPE_SECRET_KEY
        _stripe = stripe_lib
    return _stripe


def create_checkout_session(email: str, base_url: str) -> Optional[str]:
    """Create a Stripe Checkout session for a monthly subscription.
    Returns the checkout URL."""
    if not (STRIPE_SECRET_KEY and STRIPE_PRICE_ID):
        return None
    stripe = _get_stripe()
    try:
        session_obj = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            customer_email=email,
            success_url=f"{base_url.rstrip('/')}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url.rstrip('/')}/billing/canceled",
            allow_promotion_codes=True,
            metadata={"app_email": email.lower()},
        )
        return session_obj.url
    except Exception as e:
        print(f"[paywall] Stripe checkout creation failed: {e}")
        return None


def create_portal_session(email: str, base_url: str) -> Optional[str]:
    """Create a Stripe Customer Portal session for the given user."""
    if not STRIPE_SECRET_KEY:
        return None
    user = _get_user(email)
    if not user or not user.get("stripe_customer_id"):
        return None
    stripe = _get_stripe()
    try:
        portal = stripe.billing_portal.Session.create(
            customer=user["stripe_customer_id"],
            return_url=base_url.rstrip("/") + "/",
        )
        return portal.url
    except Exception as e:
        print(f"[paywall] Stripe portal creation failed: {e}")
        return None


def handle_stripe_webhook(payload_bytes: bytes, sig_header: str) -> tuple:
    """Verify signature and process the event. Returns (ok, message)."""
    if not (STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET):
        return False, "Stripe not configured"
    stripe = _get_stripe()
    try:
        event = stripe.Webhook.construct_event(payload_bytes, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return False, f"Signature verification failed: {e}"

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        # A subscription was just started
        email = (obj.get("customer_email") or obj.get("metadata", {}).get("app_email") or "").lower()
        customer_id = obj.get("customer")
        subscription_id = obj.get("subscription")
        if email:
            # Pull the subscription to get current_period_end
            end = None
            status = "active"
            if subscription_id:
                try:
                    sub = stripe.Subscription.retrieve(subscription_id)
                    end = datetime.utcfromtimestamp(sub["current_period_end"]) if sub.get("current_period_end") else None
                    status = sub.get("status", "active")
                except Exception as e:
                    print(f"[paywall] Could not retrieve subscription {subscription_id}: {e}")
            _upsert_user(
                email,
                stripe_customer_id=customer_id,
                subscription_status=status,
                subscription_current_period_end=end,
            )
        return True, "ok"

    if event_type in ("customer.subscription.updated", "customer.subscription.created"):
        status = obj.get("status", "inactive")
        end_ts = obj.get("current_period_end")
        end = datetime.utcfromtimestamp(end_ts) if end_ts else None
        customer_id = obj.get("customer")
        # Look up email via customer
        email = None
        try:
            cust = stripe.Customer.retrieve(customer_id)
            email = (cust.get("email") or "").lower()
        except Exception:
            pass
        if email:
            _upsert_user(
                email,
                stripe_customer_id=customer_id,
                subscription_status=status,
                subscription_current_period_end=end,
            )
        return True, "ok"

    if event_type == "customer.subscription.deleted":
        customer_id = obj.get("customer")
        email = None
        try:
            cust = stripe.Customer.retrieve(customer_id)
            email = (cust.get("email") or "").lower()
        except Exception:
            pass
        if email:
            _upsert_user(email, subscription_status="canceled")
        return True, "ok"

    # Not an event we act on
    return True, "ignored"


def sync_user_from_stripe(email: str) -> None:
    """Look up this email in Stripe and refresh our local record.
    Called after a successful checkout to make sure we don't have a
    race with the webhook."""
    if not STRIPE_SECRET_KEY:
        return
    stripe = _get_stripe()
    try:
        # Find customer by email
        customers = stripe.Customer.list(email=email.lower(), limit=1)
        if not customers.data:
            return
        cust = customers.data[0]
        subs = stripe.Subscription.list(customer=cust.id, status="all", limit=5)
        # Pick the most recent active/trialing sub, or the most recent overall
        active = [s for s in subs.data if s.status in ("active", "trialing")]
        sub = active[0] if active else (subs.data[0] if subs.data else None)
        if sub:
            end = datetime.utcfromtimestamp(sub["current_period_end"]) if sub.get("current_period_end") else None
            _upsert_user(
                email,
                stripe_customer_id=cust.id,
                subscription_status=sub.status,
                subscription_current_period_end=end,
            )
        else:
            _upsert_user(email, stripe_customer_id=cust.id)
    except Exception as e:
        print(f"[paywall] sync_user_from_stripe failed: {e}")


# ---------------------------------------------------------------------------
# HTML templates for auth pages
# ---------------------------------------------------------------------------
LOGIN_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Sign in — {{ brand }}</title>
<style>
:root { --navy: #27334A; --gold: #D2BC8D; --paper: #FAF6F0; --paper-2: #FFFFFF;
        --text: #1F2937; --muted: #5C6470; --line: rgba(39, 51, 74, 0.14); --rust: #9D432C; }
* { box-sizing: border-box; }
body { font-family: 'Jost', -apple-system, sans-serif; background: var(--paper);
       margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
       padding: 1.5rem; color: var(--text); }
.card { background: var(--paper-2); border: 1px solid var(--line);
        border-radius: 4px; padding: 3rem 2.5rem; width: 100%; max-width: 460px;
        box-shadow: 0 4px 24px rgba(39,51,74,0.06); }
.brand { text-align: center; margin-bottom: 2rem; }
.brand h1 { font-size: 1.6rem; letter-spacing: 0.18em; color: var(--navy);
            margin: 0; text-transform: uppercase; font-weight: 500; }
.brand .tag { color: var(--gold); font-size: 0.72rem; letter-spacing: 0.24em;
              text-transform: uppercase; margin-top: 0.4rem; }
h2 { font-size: 1.4rem; color: var(--navy); margin: 0 0 0.5rem; font-weight: 500; }
p.lead { color: var(--muted); font-size: 0.95rem; margin: 0 0 1.5rem; line-height: 1.55; }
label { display: block; font-size: 0.75rem; letter-spacing: 0.14em; text-transform: uppercase;
        color: var(--muted); margin-bottom: 0.5rem; }
input[type=email] { width: 100%; padding: 0.85rem 1rem; border: 1px solid var(--line);
                    border-radius: 2px; font-size: 1rem; font-family: inherit; outline: none;
                    background: var(--paper); transition: border-color 0.15s, box-shadow 0.15s; }
input[type=email]:focus { border-color: var(--gold); box-shadow: 0 0 0 3px rgba(210,188,141,0.18); }
button { width: 100%; padding: 0.9rem; background: var(--navy); color: var(--gold);
         border: none; border-radius: 2px; font-family: inherit; font-size: 0.8rem;
         letter-spacing: 0.14em; text-transform: uppercase; cursor: pointer;
         margin-top: 1.25rem; transition: background 0.2s; }
button:hover { background: #1a2334; }
button:disabled { opacity: 0.6; cursor: not-allowed; }
.notice { padding: 0.85rem 1rem; margin-top: 1.25rem; border-radius: 2px;
          font-size: 0.9rem; line-height: 1.5; }
.notice.ok { background: #eef7f2; color: #1f5a3f; border: 1px solid #cbe4d7; }
.notice.error { background: #fbeeeb; color: var(--rust); border: 1px solid #ecd0c8; }
.footer-note { text-align: center; font-size: 0.72rem; color: var(--muted);
               letter-spacing: 0.12em; text-transform: uppercase; margin-top: 2rem; }
</style></head>
<body>
  <div class="card">
    <div class="brand">
      <h1>{{ brand }}</h1>
      <div class="tag">Sign in</div>
    </div>
    <h2>Enter your email to continue</h2>
    <p class="lead">We'll send you a link to sign in. New subscribers can complete checkout after clicking the link.</p>
    {% if notice %}<div class="notice {{ notice_type }}">{{ notice }}</div>{% endif %}
    {% if not sent %}
    <form method="POST" action="/auth/send-link">
      <label for="email">Email address</label>
      <input type="email" id="email" name="email" required autofocus autocomplete="email" placeholder="you@example.com" />
      <button type="submit">Send sign-in link</button>
    </form>
    {% endif %}
    <div class="footer-note">By continuing you agree to receive a one-time sign-in link.</div>
  </div>
</body></html>"""

CHECKOUT_LANDING_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Subscribe — {{ brand }}</title>
<style>
:root { --navy: #27334A; --gold: #D2BC8D; --paper: #FAF6F0; --paper-2: #FFFFFF;
        --text: #1F2937; --muted: #5C6470; --line: rgba(39, 51, 74, 0.14); }
* { box-sizing: border-box; }
body { font-family: 'Jost', -apple-system, sans-serif; background: var(--paper);
       margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
       padding: 1.5rem; color: var(--text); }
.card { background: var(--paper-2); border: 1px solid var(--line);
        border-radius: 4px; padding: 3rem 2.5rem; width: 100%; max-width: 500px; text-align: center; }
h1 { font-size: 1.6rem; letter-spacing: 0.18em; color: var(--navy); margin: 0 0 0.4rem;
     text-transform: uppercase; font-weight: 500; }
.tag { color: var(--gold); font-size: 0.72rem; letter-spacing: 0.24em; text-transform: uppercase; margin-bottom: 2rem; }
h2 { font-size: 1.6rem; color: var(--navy); margin: 0 0 0.8rem; font-weight: 500; }
p { color: var(--muted); font-size: 0.98rem; line-height: 1.6; margin: 0.4rem 0 1.5rem; }
.price { font-size: 2.4rem; color: var(--navy); font-weight: 500; margin: 1.5rem 0 0.4rem; }
.price small { font-size: 1rem; color: var(--muted); font-weight: 400; }
ul { text-align: left; margin: 1.5rem auto; padding: 0 0 0 1.2rem; color: var(--text);
     font-size: 0.95rem; line-height: 1.7; max-width: 320px; }
button, a.btn { display: inline-block; width: 100%; padding: 0.95rem;
                background: var(--navy); color: var(--gold);
                border: none; border-radius: 2px; font-family: inherit;
                font-size: 0.8rem; letter-spacing: 0.14em; text-transform: uppercase;
                cursor: pointer; text-decoration: none; margin-top: 1rem; }
button:hover, a.btn:hover { background: #1a2334; }
.muted { color: var(--muted); font-size: 0.85rem; margin-top: 1.5rem; }
.muted a { color: var(--navy); }
</style></head>
<body>
  <div class="card">
    <h1>{{ brand }}</h1>
    <div class="tag">Subscribe</div>
    <h2>Unlock unlimited access</h2>
    <p>You're signed in as <strong>{{ email }}</strong>. Complete your subscription to start using {{ brand }}.</p>
    <div class="price">${{ price }}<small> /month</small></div>
    <ul>
      <li>Unlimited advisory conversations</li>
      <li>Document uploads and file attachments</li>
      <li>Cancel anytime</li>
    </ul>
    <form method="POST" action="/billing/checkout">
      <button type="submit">Continue to Stripe checkout</button>
    </form>
    <p class="muted">Not you? <a href="/auth/logout">Sign out</a></p>
  </div>
</body></html>"""
