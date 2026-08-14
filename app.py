#!/usr/bin/env python3
"""
J3P Persona Bot — with RAG knowledge base and admin panel.

NEW since persona template:
  - Document upload / chunking / embedding pipeline
  - Semantic search retrieves relevant chunks before each response
  - Admin page (password-protected) for uploads, doc management, feedback review
  - Feedback persisted to Postgres instead of just logs

NEW environment variables:
  DATABASE_URL          Auto-set by Railway when you add a Postgres plugin
  OPENAI_API_KEY        For embeddings (~$0.02/1M tokens, very cheap)
  ADMIN_PASSWORD        Password for /admin page

All other env vars from the persona template still apply.
"""
import os
from pathlib import Path
from functools import wraps
from flask import (
    Flask, request, jsonify, session, render_template_string,
    send_from_directory, redirect, url_for, flash,
)
import anthropic

import database as db
import embeddings as emb
import paywall


# Ensure paywall schema exists (no-op if DB unavailable)
try:
    paywall.ensure_schema()
except Exception as _e:
    print(f"[paywall] Schema init warning: {_e}")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_system_prompt():
    inline = os.environ.get("PERSONA_SYSTEM_PROMPT")
    if inline:
        return inline
    filename = os.environ.get("PERSONA_SYSTEM_PROMPT_FILE")
    if filename and Path(filename).exists():
        return Path(filename).read_text(encoding="utf-8")
    try:
        from system_prompt import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    except ImportError:
        pass
    return "You are a helpful assistant."


CONFIG = {
    "persona_name": os.environ.get("PERSONA_NAME", "J3P Advisor"),
    "opening": os.environ.get(
        "PERSONA_OPENING",
        "Hello, welcome to your session with the J3P Advisor.",
    ),
    "placeholder": os.environ.get("PERSONA_PLACEHOLDER", "How can I help you?"),
    "system_prompt": load_system_prompt(),

    "logo_url": os.environ.get("BRAND_LOGO_URL", "/full_logo.png"),
    "favicon_url": os.environ.get("BRAND_FAVICON_URL", "/monogram.jpg"),
    "navy": os.environ.get("BRAND_NAVY", "#27334A"),
    "gold": os.environ.get("BRAND_GOLD", "#D2BC8D"),
    "paper": os.environ.get("BRAND_PAPER", "#FAF6F0"),

    "footer_disclaimer": os.environ.get(
        "FOOTER_DISCLAIMER",
        "For informational purposes only. Not medical, legal, or financial advice.",
    ),
    "footer_cta_text": os.environ.get(
        "FOOTER_CTA_TEXT",
        "To schedule time with a J3P Advisor, please",
    ),
    "footer_cta_url": os.environ.get(
        "FOOTER_CTA_URL",
        "https://calendly.com/afriedmanj3p/30min?month=2026-07",
    ),

    "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
    "max_tokens": int(os.environ.get("MAX_TOKENS", "1024")),
    "rag_top_k": int(os.environ.get("RAG_TOP_K", "4")),
    "rag_min_similarity": float(os.environ.get("RAG_MIN_SIMILARITY", "0.3")),
    "admin_password": os.environ.get("ADMIN_PASSWORD", ""),
}


# ---------------------------------------------------------------------------
# App setup — initialize DB schema on startup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload cap
client = anthropic.Anthropic()

# Initialize DB schema once at startup (idempotent)
try:
    if db.is_enabled():
        db.init_schema()
        app.logger.info("Database schema initialized")
    else:
        app.logger.warning("Database not configured — RAG and feedback persistence disabled")
except Exception as e:
    app.logger.error(f"DB init failed: {e}")


# ---------------------------------------------------------------------------
# Auth helper for admin routes
# ---------------------------------------------------------------------------

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not CONFIG["admin_password"]:
            return ("Admin disabled. Set ADMIN_PASSWORD environment variable.", 503)
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Main chat HTML
# ---------------------------------------------------------------------------

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{ cfg.persona_name }}</title>
  <link rel="icon" href="{{ cfg.favicon_url }}" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --navy: {{ cfg.navy }};
      --gold: {{ cfg.gold }};
      --paper: {{ cfg.paper }};
      --paper-2: #FFFFFF;
      --line: rgba(39, 51, 74, 0.12);
      --muted: #6B7280;
      --text: #27334A;
      --rust: #9D432C;
      --shadow: 0 1px 2px rgba(39, 51, 74, 0.05), 0 8px 28px rgba(39, 51, 74, 0.07);
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      font-family: 'Jost', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--paper); color: var(--text);
      display: flex; flex-direction: column;
      font-size: 15px; line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }
    header {
      background: var(--navy); color: var(--paper-2);
      padding: 1rem 1.75rem;
      display: flex; justify-content: space-between; align-items: center;
      border-bottom: 2px solid var(--gold);
      gap: 0.75rem;
    }
    .brand { display: flex; align-items: center; gap: 1rem; min-width: 0; flex: 1; }
    .brand-logo { height: 60px; width: auto; display: block; flex-shrink: 0; }
    .brand-divider { width: 1px; height: 38px; background: rgba(210, 188, 141, 0.35); flex-shrink: 0; }
    .brand-tag {
      font-size: 0.92rem; letter-spacing: 0.22em;
      text-transform: uppercase; color: var(--gold);
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    header button {
      background: transparent; color: var(--paper-2);
      border: 1px solid rgba(210, 188, 141, 0.35);
      padding: 0.5rem 1rem; border-radius: 2px;
      cursor: pointer; font-size: 0.75rem;
      font-family: inherit; letter-spacing: 0.14em;
      text-transform: uppercase; transition: all 0.2s ease;
      flex-shrink: 0; white-space: nowrap;
      display: inline-flex; align-items: center; gap: 0.4rem;
    }
    header button:hover {
      background: rgba(210, 188, 141, 0.08);
      border-color: var(--gold); color: var(--gold);
    }
    /* Show full label on desktop, icon-only label on small screens */
    .reset-icon { width: 16px; height: 16px; display: none; }
    .reset-label { display: inline; }
    .autospeak-icon { width: 16px; height: 16px; }
    .autospeak-label { display: inline; }
    /* Highlight the auto-speak button when it's ON */
    #autospeak-btn.on {
      background: var(--gold);
      color: var(--navy);
      border-color: var(--gold);
    }
    #autospeak-btn.on:hover {
      background: var(--gold);
      color: var(--navy);
    }
    #chat-wrap { flex: 1; overflow-y: auto; }
    #chat { max-width: 760px; margin: 0 auto; padding: 2.25rem 1.5rem 1rem; }
    .msg {
      margin-bottom: 1.25rem; padding: 1rem 1.2rem; border-radius: 4px;
      white-space: pre-wrap; word-wrap: break-word; font-size: 0.95rem;
      animation: fadeIn 0.3s ease-out;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    .user { background: var(--navy); color: var(--paper); margin-left: 18%; box-shadow: var(--shadow); }
    .assistant {
      background: var(--paper-2); border: 1px solid var(--line);
      margin-right: 12%; box-shadow: var(--shadow); position: relative;
    }
    .assistant::before {
      content: ""; position: absolute; left: 0; top: 0; bottom: 0;
      width: 3px; background: var(--gold);
    }
    .typing { color: var(--muted); font-style: italic; }
    .feedback {
      display: flex; align-items: center;
      gap: 0.5rem; margin-top: 0.6rem;
      padding-top: 0.6rem; border-top: 1px solid var(--line);
      flex-wrap: wrap;
    }
    .feedback-label {
      font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase;
      color: var(--muted); margin-right: 0.3rem;
    }
    .feedback-btn {
      background: transparent; border: 1px solid var(--line);
      color: var(--muted); width: 30px; height: 30px; border-radius: 50%;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      padding: 0; transition: all 0.18s ease;
    }
    .feedback-btn svg { width: 14px; height: 14px; }
    .feedback-btn:hover { border-color: var(--gold); color: var(--navy); background: var(--paper); }
    .feedback-btn.selected-up { background: var(--navy); border-color: var(--navy); color: var(--gold); }
    .feedback-btn.selected-down { background: var(--rust); border-color: var(--rust); color: #fff; }
    .feedback-btn:disabled { cursor: default; }
    .feedback-thanks { font-size: 0.7rem; color: var(--muted); margin-left: 0.4rem; font-style: italic; }

    /* Action buttons (copy + share) — labeled pill style */
    .action-sep {
      width: 1px; height: 22px; background: var(--line);
      margin: 0 0.3rem;
    }
    .action-btn {
      background: transparent;
      border: 1px solid var(--line);
      color: var(--muted);
      padding: 0.4rem 0.85rem;
      border-radius: 4px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-family: inherit;
      font-size: 0.7rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      transition: all 0.18s ease;
      white-space: nowrap;
    }
    .action-btn svg { width: 14px; height: 14px; }
    .action-btn:hover {
      border-color: var(--gold);
      color: var(--navy);
      background: var(--paper);
    }
    .action-btn.copied {
      background: var(--navy);
      border-color: var(--navy);
      color: var(--gold);
    }
    .action-btn.copied:hover {
      background: var(--navy); color: var(--gold);
    }
    .action-btn.speaking {
      background: var(--navy);
      border-color: var(--navy);
      color: var(--gold);
      animation: speak-pulse 1.4s ease-in-out infinite;
    }
    .action-btn.speaking:hover { background: var(--navy); color: var(--gold); }
    .action-btn.paused {
      background: var(--paper);
      border-color: var(--gold);
      color: var(--navy);
    }
    @keyframes speak-pulse {
      0%, 100% { box-shadow: 0 0 0 0 rgba(210, 188, 141, 0); }
      50%      { box-shadow: 0 0 0 6px rgba(210, 188, 141, 0.28); }
    }

    /* Share menu popover */
    .share-wrap { position: relative; display: inline-block; }
    .share-menu {
      position: absolute; bottom: calc(100% + 8px); right: 0;
      background: var(--paper-2); border: 1px solid var(--line);
      border-radius: 4px; box-shadow: var(--shadow);
      padding: 0.4rem; min-width: 180px;
      display: none; flex-direction: column; gap: 0.1rem;
      z-index: 10;
    }
    .share-menu.open { display: flex; }
    .share-menu a, .share-menu button {
      display: flex; align-items: center; gap: 0.6rem;
      padding: 0.5rem 0.7rem; border-radius: 2px;
      background: transparent; border: none; cursor: pointer;
      color: var(--text); font-size: 0.82rem;
      font-family: inherit; text-decoration: none;
      text-align: left; width: 100%;
      letter-spacing: 0; text-transform: none;
    }
    .share-menu a:hover, .share-menu button:hover { background: var(--paper); color: var(--navy); }
    .share-menu svg { width: 16px; height: 16px; flex-shrink: 0; color: var(--muted); }

    /* On the feedback row, push actions to the right */
    .feedback-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .feedback-comment {
      margin-top: 0.7rem;
      padding-top: 0.7rem;
      border-top: 1px dashed var(--line);
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .feedback-comment label {
      font-size: 0.72rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .feedback-comment textarea {
      width: 100%;
      padding: 0.6rem 0.75rem;
      border: 1px solid var(--line);
      border-radius: 4px;
      font-family: inherit;
      font-size: 0.9rem;
      outline: none;
      resize: vertical;
      min-height: 64px;
      background: var(--paper);
      color: var(--text);
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .feedback-comment textarea:focus {
      border-color: var(--rust);
      box-shadow: 0 0 0 3px rgba(157, 67, 44, 0.12);
    }
    .feedback-comment-actions {
      display: flex;
      gap: 0.5rem;
      align-items: center;
    }
    .feedback-comment-btn {
      background: var(--rust);
      color: #fff;
      border: 1px solid var(--rust);
      border-radius: 2px;
      padding: 0.45rem 0.95rem;
      font-size: 0.7rem;
      font-family: inherit;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      cursor: pointer;
      transition: opacity 0.15s ease;
    }
    .feedback-comment-btn:hover:not(:disabled) { opacity: 0.85; }
    .feedback-comment-btn.secondary {
      background: transparent;
      color: var(--muted);
      border-color: var(--line);
    }
    .feedback-comment-btn:disabled { opacity: 0.5; cursor: default; }
    .composer-wrap { background: var(--paper-2); border-top: 1px solid var(--line); }
    form { display: flex; gap: 0.6rem; padding: 1rem 1.5rem; max-width: 760px; margin: 0 auto; }
    .input-wrap { flex: 1; position: relative; display: flex; align-items: center; }
    .attach-btn {
      position: absolute; right: 3rem; top: 50%; transform: translateY(-50%);
      background: transparent; border: none;
      color: var(--muted); cursor: pointer;
      width: 32px; height: 32px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s ease; padding: 0;
    }
    .attach-btn:hover { color: var(--navy); background: var(--paper); }
    .attach-btn svg { width: 18px; height: 18px; }
    .folder-btn {
      position: absolute; right: 5rem; top: 50%; transform: translateY(-50%);
      background: transparent; border: none;
      color: var(--muted); cursor: pointer;
      width: 32px; height: 32px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s ease; padding: 0;
    }
    .folder-btn:hover { color: var(--navy); background: var(--paper); }
    .folder-btn svg { width: 18px; height: 18px; }
    #file-input, #folder-input-chat { display: none; }
    .attached-file {
      display: none; align-items: center; gap: 0.5rem;
      background: var(--paper); border: 1px solid var(--line);
      border-radius: 4px; padding: 0.4rem 0.6rem;
      margin: 0 1.75rem 0.5rem; font-size: 0.82rem;
      color: var(--navy);
    }
    .attached-file.visible { display: inline-flex; }
    .attached-file svg { width: 14px; height: 14px; color: var(--muted); flex-shrink: 0; }
    .attached-file .filename { max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .attached-file .filesize { color: var(--muted); font-size: 0.72rem; }
    .attached-file button {
      background: transparent; border: none; cursor: pointer;
      color: var(--muted); padding: 2px; display: flex;
      align-items: center; justify-content: center;
    }
    .attached-file button:hover { color: var(--rust); }
    .attached-file button svg { width: 14px; height: 14px; }
    input[type="text"] {
      flex: 1; padding: 0.85rem 7.6rem 0.85rem 1.1rem;
      border: 1px solid var(--line); border-radius: 2px;
      font-size: 0.95rem; font-family: inherit; outline: none;
      background: var(--paper); color: var(--text); width: 100%;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    input[type="text"]:focus { border-color: var(--gold); box-shadow: 0 0 0 3px rgba(210, 188, 141, 0.18); }
    .mic-btn {
      position: absolute; right: 6px; top: 50%; transform: translateY(-50%);
      width: 38px; height: 38px; display: flex; align-items: center;
      justify-content: center; background: var(--navy); color: var(--gold);
      border: none; border-radius: 50%; cursor: pointer; padding: 0;
      transition: all 0.2s ease;
    }
    .mic-btn:hover { background: var(--gold); color: var(--navy); }
    .mic-btn svg { width: 18px; height: 18px; }
    .mic-btn.recording { background: var(--rust); color: #fff; animation: pulse 1.2s ease-in-out infinite; }
    .mic-btn.unsupported { display: none; }
    @keyframes pulse {
      0%, 100% { box-shadow: 0 0 0 0 rgba(157, 67, 44, 0.6); }
      50% { box-shadow: 0 0 0 8px rgba(157, 67, 44, 0); }
    }
    button[type="submit"] {
      padding: 0.85rem 1.75rem; background: var(--navy); color: var(--gold);
      border: 1px solid var(--navy); border-radius: 2px;
      font-size: 0.78rem; font-family: inherit; letter-spacing: 0.18em;
      text-transform: uppercase; cursor: pointer; transition: all 0.2s ease;
    }
    button[type="submit"]:hover:not(:disabled) { background: var(--gold); color: var(--navy); }
    button[type="submit"]:disabled { opacity: 0.5; cursor: not-allowed; }
    .footer-note {
      text-align: center; font-size: 0.68rem; color: var(--muted);
      padding: 0 1rem 0.9rem; letter-spacing: 0.14em;
      text-transform: uppercase; line-height: 1.7;
    }
    .footer-note a { color: var(--navy); text-decoration: none; border-bottom: 1px solid var(--gold); }
    .footer-note a:hover { color: var(--rust); }
    @media (max-width: 640px) {
      .user { margin-left: 8%; } .assistant { margin-right: 6%; }
      header { padding: 0.75rem 0.9rem; gap: 0.5rem; }
      .brand-logo { height: 40px; }
      .brand-tag { font-size: 0.7rem; letter-spacing: 0.18em; }
      .brand { gap: 0.6rem; } .brand-divider { height: 26px; }
      header button { padding: 0.45rem 0.7rem; font-size: 0.68rem; letter-spacing: 0.1em; }
      #chat { padding: 1.5rem 1rem 0.75rem; }
      form { padding: 0.75rem 1rem; gap: 0.4rem; }
      input[type="text"] { padding: 0.75rem 7.2rem 0.75rem 0.9rem; font-size: 16px; }
      button[type="submit"] { padding: 0.75rem 1rem; font-size: 0.7rem; letter-spacing: 0.12em; }
      .footer-note { font-size: 0.62rem; letter-spacing: 0.1em; }
    }
    /* Very narrow phones: hide the persona tag + divider, swap button to icon only */
    @media (max-width: 480px) {
      .brand-divider, .brand-tag { display: none; }
      .reset-label { display: none; }
      .reset-icon { display: inline-block; }
      .autospeak-label { display: none; }
      header button { padding: 0.5rem; min-width: 38px; min-height: 38px;
                      display: inline-flex; align-items: center; justify-content: center; }
      /* Hide action button text labels — keep icons only */
      .action-btn span { display: none; }
      .action-btn { padding: 0.45rem 0.55rem; }
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <img src="{{ cfg.logo_url }}" alt="{{ cfg.persona_name }}" class="brand-logo" />
      <span class="brand-divider"></span>
      <span class="brand-tag">{{ cfg.persona_name }}</span>
    </div>
    <button id="autospeak-btn" aria-label="Toggle auto read-aloud" title="Toggle auto read-aloud for every response">
      <svg class="autospeak-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
      </svg>
      <span class="autospeak-label">Auto-speak</span>
    </button>
    <button id="reset-btn" aria-label="Start a new conversation" title="New conversation">
      <svg class="reset-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 5v14M5 12h14"/>
      </svg>
      <span class="reset-label">New conversation</span>
    </button>
  </header>

  <div id="chat-wrap">
    <div id="chat">
      <div class="msg assistant">{{ cfg.opening }}</div>
    </div>
  </div>

  <div class="composer-wrap">
    <div id="attached-file" class="attached-file" aria-live="polite">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      <span class="filename" id="attached-file-name">document.pdf</span>
      <span class="filesize" id="attached-file-size"></span>
      <button type="button" id="remove-file-btn" aria-label="Remove attachment" title="Remove">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <form id="chat-form">
      <div class="input-wrap">
        <input type="text" id="message" placeholder="{{ cfg.placeholder }}" autocomplete="off" autofocus />
        <input type="file" id="file-input" accept=".pdf,.docx,.txt,.md,.jpg,.jpeg,.png,.gif,.webp" multiple />
        <input type="file" id="folder-input-chat" webkitdirectory directory multiple />
        <button type="button" id="folder-btn" class="folder-btn" aria-label="Attach folder" title="Attach a folder of documents">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
        </button>
        <button type="button" id="attach-btn" class="attach-btn" aria-label="Attach file" title="Attach a document or image">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.44 11.05 12.25 20.24a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
          </svg>
        </button>
        <button type="button" id="mic-btn" class="mic-btn" aria-label="Voice input" title="Click to speak">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
        </button>
      </div>
      <button type="submit" id="send-btn">Send</button>
    </form>
    <div class="footer-note">
      {{ cfg.footer_disclaimer }}<br />
      {{ cfg.footer_cta_text }} <a href="{{ cfg.footer_cta_url }}" target="_blank" rel="noopener">click here</a>.
    </div>
  </div>

  <script>
    const chat = document.getElementById("chat");
    const form = document.getElementById("chat-form");
    const input = document.getElementById("message");
    const sendBtn = document.getElementById("send-btn");
    const resetBtn = document.getElementById("reset-btn");
    const chatWrap = document.getElementById("chat-wrap");
    const OPENING = {{ cfg.opening|tojson }};

    // -------------------------------------------------------------
    // Speech synthesis: consistent voice selection + auto-speak toggle
    // -------------------------------------------------------------
    // Prefer named professional voices, in order. If none exist, fall back
    // to the browser default. Chosen for clarity + a warm advisor feel.
    const PREFERRED_VOICES = [
      "Samantha",           // macOS / iOS (default American female)
      "Karen",              // macOS / iOS (Australian, warmer)
      "Google US English",  // Chrome / Android
      "Microsoft Zira",     // Windows
      "Microsoft Aria",     // Windows 11
    ];
    let __preferredVoice = null;
    function pickVoice() {
      if (!("speechSynthesis" in window)) return null;
      const voices = window.speechSynthesis.getVoices() || [];
      if (!voices.length) return null;
      for (const name of PREFERRED_VOICES) {
        const match = voices.find(v => v.name === name || v.name.startsWith(name));
        if (match) return match;
      }
      // Fall back to first English voice, then anything
      return voices.find(v => (v.lang || "").toLowerCase().startsWith("en"))
          || voices[0]
          || null;
    }
    // Voices may load async — refresh once they arrive
    if ("speechSynthesis" in window) {
      __preferredVoice = pickVoice();
      window.speechSynthesis.onvoiceschanged = () => { __preferredVoice = pickVoice(); };
    }
    // Expose to speak buttons on individual messages
    window.__pickPreferredVoice = () => __preferredVoice;

    // Auto-speak state — persists across visits
    const autoSpeakBtn = document.getElementById("autospeak-btn");
    let autoSpeakEnabled = false;
    try {
      autoSpeakEnabled = localStorage.getItem("j3p_autospeak") === "1";
    } catch (e) { /* localStorage may be blocked; fall back to session default */ }
    function refreshAutoSpeakUI() {
      if (!autoSpeakBtn) return;
      if (autoSpeakEnabled) {
        autoSpeakBtn.classList.add("on");
        autoSpeakBtn.title = "Auto read-aloud is ON — click to turn off";
      } else {
        autoSpeakBtn.classList.remove("on");
        autoSpeakBtn.title = "Auto read-aloud is OFF — click to turn on";
      }
    }
    refreshAutoSpeakUI();
    // If browser doesn't support speech, hide the toggle
    if (!("speechSynthesis" in window)) {
      if (autoSpeakBtn) autoSpeakBtn.style.display = "none";
      autoSpeakEnabled = false;
    } else if (autoSpeakBtn) {
      autoSpeakBtn.addEventListener("click", () => {
        autoSpeakEnabled = !autoSpeakEnabled;
        try { localStorage.setItem("j3p_autospeak", autoSpeakEnabled ? "1" : "0"); } catch (e) {}
        refreshAutoSpeakUI();
        // Turning OFF should stop anything currently speaking
        if (!autoSpeakEnabled && window.speechSynthesis) {
          window.speechSynthesis.cancel();
          if (window.__activeSpeakBtn) {
            const prev = window.__activeSpeakBtn;
            prev.classList.remove("speaking", "paused");
            const lbl = prev.querySelector(".speak-label");
            if (lbl) lbl.textContent = "Speak";
            window.__activeSpeakBtn = null;
          }
        }
      });
    }
    // Expose to addMessage so a new bot reply can auto-play when enabled
    window.__isAutoSpeakOn = () => autoSpeakEnabled;

    function addMessage(text, role, withFeedback = false, interactionId = null) {
      const div = document.createElement("div");
      div.className = "msg " + role;
      if (interactionId) div.dataset.interactionId = String(interactionId);
      const textNode = document.createElement("div");
      textNode.textContent = text;
      div.appendChild(textNode);
      if (withFeedback) attachFeedback(div, text, interactionId);
      chat.appendChild(div);
      chatWrap.scrollTop = chatWrap.scrollHeight;
      // If auto-speak is enabled and this is a fresh assistant reply (with feedback
      // row, meaning it was just received from the API), start reading it aloud.
      // A tiny delay gives the DOM time to attach the speak button.
      if (withFeedback && role.startsWith("assistant") && window.__isAutoSpeakOn && window.__isAutoSpeakOn()) {
        setTimeout(() => {
          const sb = div.querySelector(".speak-btn");
          if (sb) sb.click();
        }, 60);
      }
      return div;
    }

    function attachFeedback(msgDiv, replyText, interactionId) {
      const wrap = document.createElement("div");
      wrap.className = "feedback";
      wrap.innerHTML = `
        <span class="feedback-label">Helpful?</span>
        <button class="feedback-btn" data-rating="up" aria-label="Thumbs up" title="Yes, helpful">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H7v-12L11.69 2.5a2 2 0 0 1 3.31 3.38z"/>
          </svg>
        </button>
        <button class="feedback-btn" data-rating="down" aria-label="Thumbs down" title="No, not helpful">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H17v12l-4.69 7.5a2 2 0 0 1-3.31-3.38z"/>
          </svg>
        </button>
        <button class="action-btn speak-btn" style="margin-left: auto;" aria-label="Read answer aloud" title="Read answer aloud">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
          </svg>
          <span class="speak-label">Speak</span>
        </button>
        <button class="action-btn copy-btn" aria-label="Copy answer" title="Copy answer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
          <span class="copy-label">Copy</span>
        </button>
        <span class="share-wrap">
          <button class="action-btn share-btn" aria-label="Share answer" title="Share answer">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
            </svg>
            <span>Share</span>
          </button>
          <div class="share-menu" role="menu"></div>
        </span>
      `;

      async function sendFeedback(rating, comment) {
        try {
          await fetch("/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              rating, reply: replyText, comment: comment || "",
              interaction_id: interactionId || null,
            }),
          });
        } catch (err) {
          console.error("Feedback error:", err);
        }
      }

      const buttons = wrap.querySelectorAll(".feedback-btn");
      buttons.forEach(btn => {
        btn.addEventListener("click", async () => {
          if (btn.disabled) return;
          const rating = btn.dataset.rating;

          if (rating === "up") {
            // Thumbs up: simple submit, no comment needed
            buttons.forEach(b => { b.disabled = true; });
            btn.classList.add("selected-up");
            await sendFeedback("up", "");
            const thanks = document.createElement("span");
            thanks.className = "feedback-thanks";
            thanks.textContent = "Thanks for the feedback";
            wrap.appendChild(thanks);
          } else {
            // Thumbs down: show comment field, don't submit yet
            buttons.forEach(b => { b.disabled = true; });
            btn.classList.add("selected-down");

            const commentBox = document.createElement("div");
            commentBox.className = "feedback-comment";
            commentBox.innerHTML = `
              <label>What was wrong? (optional)</label>
              <textarea placeholder="Tell us what would have been more helpful..." maxlength="2000"></textarea>
              <div class="feedback-comment-actions">
                <button type="button" class="feedback-comment-btn" data-action="submit">Submit feedback</button>
                <button type="button" class="feedback-comment-btn secondary" data-action="skip">Skip</button>
              </div>
            `;
            wrap.appendChild(commentBox);

            const textarea = commentBox.querySelector("textarea");
            textarea.focus();

            const submitBtn = commentBox.querySelector('[data-action="submit"]');
            const skipBtn = commentBox.querySelector('[data-action="skip"]');

            async function finalize(commentText) {
              submitBtn.disabled = true;
              skipBtn.disabled = true;
              textarea.disabled = true;
              await sendFeedback("down", commentText);
              commentBox.innerHTML = '<span class="feedback-thanks">Thanks for the feedback</span>';
            }

            submitBtn.addEventListener("click", () => finalize(textarea.value.trim()));
            skipBtn.addEventListener("click", () => finalize(""));
            textarea.addEventListener("keydown", (e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                finalize(textarea.value.trim());
              }
            });
          }
        });
      });
      // === SPEAK button (browser text-to-speech) ===
      const speakBtn = wrap.querySelector(".speak-btn");
      const speakLabel = speakBtn ? speakBtn.querySelector(".speak-label") : null;
      const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
      if (!canSpeak && speakBtn) {
        // Browser doesn't support speech synthesis — hide the button entirely
        speakBtn.style.display = "none";
      } else if (speakBtn) {
        // Strip markdown so the reader doesn't literally say "star star bold star star"
        const stripMarkdown = (t) => (t || "")
          .replace(/```[\s\S]*?```/g, " ")             // fenced code blocks
          .replace(/\*\*(.+?)\*\*/g, "$1")             // **bold**
          .replace(/__([^_]+?)__/g, "$1")              // __bold__
          .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "$1")  // *italic*
          .replace(/(?<!_)_(?!_)([^_]+?)(?<!_)_(?!_)/g, "$1")     // _italic_
          .replace(/^#{1,6}\s+/gm, "")                 // # headers
          .replace(/`([^`]+?)`/g, "$1")                // `inline code`
          .replace(/^[-*+]\s+/gm, "")                  // bullet markers
          .replace(/^\d+\.\s+/gm, "")                  // numbered list markers
          .replace(/\[([^\]]+?)\]\([^)]+?\)/g, "$1")   // [text](url) -> text
          .replace(/^-{3,}\s*$/gm, ". ")               // horizontal rules
          .replace(/\n{2,}/g, ". ")                    // paragraph breaks -> pause
          .replace(/\n/g, " ")                         // remaining newlines
          .replace(/\s{2,}/g, " ")
          .trim();

        function resetSpeakUI() {
          speakBtn.classList.remove("speaking", "paused");
          if (speakLabel) speakLabel.textContent = "Speak";
        }

        speakBtn.addEventListener("click", () => {
          const synth = window.speechSynthesis;

          // If THIS button is currently speaking or paused → toggle
          if (window.__activeSpeakBtn === speakBtn) {
            if (synth.paused) {
              synth.resume();
              speakBtn.classList.add("speaking");
              speakBtn.classList.remove("paused");
              if (speakLabel) speakLabel.textContent = "Speaking";
            } else if (synth.speaking) {
              synth.pause();
              speakBtn.classList.remove("speaking");
              speakBtn.classList.add("paused");
              if (speakLabel) speakLabel.textContent = "Paused";
            }
            return;
          }

          // A different message was speaking — stop it first
          if (window.__activeSpeakBtn && window.__activeSpeakBtn !== speakBtn) {
            const prev = window.__activeSpeakBtn;
            prev.classList.remove("speaking", "paused");
            const prevLabel = prev.querySelector(".speak-label");
            if (prevLabel) prevLabel.textContent = "Speak";
          }
          synth.cancel();

          const utter = new SpeechSynthesisUtterance(stripMarkdown(replyText));
          utter.rate = 1.0;
          utter.pitch = 1.0;
          utter.volume = 1.0;
          // Consistent voice across devices (falls through to browser default if unavailable)
          const pv = (typeof window.__pickPreferredVoice === "function") ? window.__pickPreferredVoice() : null;
          if (pv) utter.voice = pv;
          utter.onend = () => {
            resetSpeakUI();
            if (window.__activeSpeakBtn === speakBtn) window.__activeSpeakBtn = null;
          };
          utter.onerror = () => {
            resetSpeakUI();
            if (window.__activeSpeakBtn === speakBtn) window.__activeSpeakBtn = null;
          };
          synth.speak(utter);
          window.__activeSpeakBtn = speakBtn;
          speakBtn.classList.add("speaking");
          if (speakLabel) speakLabel.textContent = "Speaking";
        });
      }

      // === COPY button ===
      const copyBtn = wrap.querySelector(".copy-btn");
      const copyLabel = copyBtn.querySelector(".copy-label");
      copyBtn.addEventListener("click", async () => {
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(replyText);
          } else {
            // Fallback for older browsers / non-HTTPS contexts
            const ta = document.createElement("textarea");
            ta.value = replyText; ta.style.position = "fixed"; ta.style.opacity = "0";
            document.body.appendChild(ta); ta.select();
            document.execCommand("copy"); document.body.removeChild(ta);
          }
          copyBtn.classList.add("copied");
          copyLabel.textContent = "Copied";
          setTimeout(() => {
            copyBtn.classList.remove("copied");
            copyLabel.textContent = "Copy";
          }, 1600);
        } catch (err) {
          console.error("Copy failed:", err);
          copyLabel.textContent = "Failed";
          setTimeout(() => { copyLabel.textContent = "Copy"; }, 1600);
        }
      });

      // === SHARE button ===
      const shareBtn = wrap.querySelector(".share-btn");
      const shareMenu = wrap.querySelector(".share-menu");
      const shareTitle = "From J3P Advisor";
      // Truncate share text to keep social/SMS messages under sane limits
      const shareText = replyText.length > 600
        ? replyText.slice(0, 600).trim() + "…"
        : replyText;
      const shareUrl = window.location.origin;

      shareBtn.addEventListener("click", async () => {
        // Try native share sheet first (mobile + modern desktop browsers)
        if (navigator.share) {
          try {
            await navigator.share({ title: shareTitle, text: shareText, url: shareUrl });
            return;
          } catch (err) {
            // User cancelled or share failed — fall through to menu
            if (err.name === "AbortError") return;
          }
        }
        // Fallback menu for desktop browsers without Web Share API
        if (shareMenu.classList.contains("open")) {
          shareMenu.classList.remove("open");
          return;
        }
        const emailSubject = encodeURIComponent(shareTitle);
        const emailBody = encodeURIComponent(shareText + "\\n\\n" + shareUrl);
        const smsBody = encodeURIComponent(shareText + " " + shareUrl);
        const twText = encodeURIComponent(shareText.slice(0, 240) + " " + shareUrl);
        const liUrl = encodeURIComponent(shareUrl);
        const fbUrl = encodeURIComponent(shareUrl);

        shareMenu.innerHTML = `
          <a href="mailto:?subject=${emailSubject}&body=${emailBody}" role="menuitem">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
            Email
          </a>
          <a href="sms:?body=${smsBody}" role="menuitem">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            Text message
          </a>
          <a href="https://twitter.com/intent/tweet?text=${twText}" target="_blank" rel="noopener" role="menuitem">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
            X / Twitter
          </a>
          <a href="https://www.linkedin.com/sharing/share-offsite/?url=${liUrl}" target="_blank" rel="noopener" role="menuitem">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.063 2.063 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
            LinkedIn
          </a>
          <a href="https://www.facebook.com/sharer/sharer.php?u=${fbUrl}" target="_blank" rel="noopener" role="menuitem">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
            Facebook
          </a>
          <button type="button" data-action="copy-link" role="menuitem">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
            Copy link
          </button>
        `;
        shareMenu.classList.add("open");

        const copyLinkBtn = shareMenu.querySelector('[data-action="copy-link"]');
        if (copyLinkBtn) {
          copyLinkBtn.addEventListener("click", async () => {
            try {
              await navigator.clipboard.writeText(shareUrl);
              copyLinkBtn.textContent = "Link copied";
            } catch (err) { console.error(err); }
            setTimeout(() => shareMenu.classList.remove("open"), 700);
          });
        }
      });

      // Close share menu when clicking outside
      document.addEventListener("click", (e) => {
        if (!wrap.contains(e.target)) shareMenu.classList.remove("open");
      });

      msgDiv.appendChild(wrap);
    }

    // Attach file / folder handling
    const fileInput = document.getElementById("file-input");
    const folderInput = document.getElementById("folder-input-chat");
    const attachBtn = document.getElementById("attach-btn");
    const folderBtn = document.getElementById("folder-btn");
    const attachedFileDiv = document.getElementById("attached-file");
    const attachedFileName = document.getElementById("attached-file-name");
    const attachedFileSize = document.getElementById("attached-file-size");
    const removeFileBtn = document.getElementById("remove-file-btn");
    const MAX_FILE_MB = 25;
    const MAX_FOLDER_FILES = 20;
    const DOC_RE = /\.(pdf|docx|txt|md)$/i;
    // Track state: either a single file OR a list of folder files, never both
    let attachedFolderFiles = [];   // list of File objects when a folder is picked
    let attachedFolderName = "";

    function formatFileSize(bytes) {
      if (bytes < 1024) return bytes + " B";
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
      return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }
    function clearAttachment() {
      fileInput.value = "";
      folderInput.value = "";
      attachedFolderFiles = [];
      attachedFolderName = "";
      attachedFileDiv.classList.remove("visible");
    }

    attachBtn.addEventListener("click", () => {
      clearAttachment();          // clear any prior folder selection
      fileInput.click();
    });
    folderBtn.addEventListener("click", () => {
      clearAttachment();          // clear any prior single-file selection
      folderInput.click();
    });
    removeFileBtn.addEventListener("click", clearAttachment);

    fileInput.addEventListener("change", () => {
      const all = Array.from(fileInput.files || []);
      if (all.length === 0) return;
      // Validate every file
      const okRe = /\.(pdf|docx|txt|md|jpe?g|png|gif|webp)$/i;
      const bad = all.filter(f => !okRe.test(f.name));
      if (bad.length) {
        alert("One or more files are unsupported. Please attach only PDF, DOCX, TXT, MD, or images (JPG, PNG, GIF, WEBP).");
        clearAttachment(); return;
      }
      const oversized = all.filter(f => f.size > MAX_FILE_MB * 1024 * 1024);
      if (oversized.length) {
        alert(`One or more files exceed ${MAX_FILE_MB} MB: ${oversized.map(f => f.name).join(", ")}`);
        clearAttachment(); return;
      }
      // Show a friendly summary in the pill
      if (all.length === 1) {
        attachedFileName.textContent = all[0].name;
        attachedFileSize.textContent = "· " + formatFileSize(all[0].size);
      } else {
        const totalBytes = all.reduce((sum, f) => sum + f.size, 0);
        attachedFileName.textContent = `${all.length} files: ` + all.slice(0, 3).map(f => f.name).join(", ") + (all.length > 3 ? "…" : "");
        attachedFileSize.textContent = "· " + formatFileSize(totalBytes);
      }
      attachedFileDiv.classList.add("visible");
    });

    folderInput.addEventListener("change", () => {
      const all = Array.from(folderInput.files || []);
      // Filter to documents only (images not supported in folder-attach mode)
      const docs = all.filter(f => DOC_RE.test(f.name));
      if (docs.length === 0) {
        alert("No supported documents found in this folder (PDF, DOCX, TXT, MD).");
        clearAttachment(); return;
      }
      const capped = docs.slice(0, MAX_FOLDER_FILES);
      // webkitRelativePath looks like "FolderName/sub/file.pdf" — extract the top-level folder name
      const first = capped[0].webkitRelativePath || capped[0].name;
      const folderName = first.split("/")[0] || "Folder";
      attachedFolderFiles = capped;
      attachedFolderName = folderName;
      let msg = `${folderName} · ${capped.length} file${capped.length === 1 ? "" : "s"}`;
      if (docs.length > MAX_FOLDER_FILES) msg += ` (first ${MAX_FOLDER_FILES} only)`;
      if (docs.length < all.length) msg += ` · ${all.length - docs.length} skipped`;
      attachedFileName.textContent = msg;
      attachedFileSize.textContent = "";
      attachedFileDiv.classList.add("visible");
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = input.value.trim();
      const paperclipFiles = Array.from(fileInput.files || []);
      const folderFiles = attachedFolderFiles.slice();
      const folderName = attachedFolderName;
      // Require at least one of: text, single/multi file(s), or folder
      if (!text && paperclipFiles.length === 0 && folderFiles.length === 0) return;

      // Build the message shown in chat
      let displayText;
      if (folderFiles.length > 0) {
        displayText = (text || "[No message]") +
          `\n\n📂 Attached folder: ${folderName} (${folderFiles.length} file${folderFiles.length === 1 ? "" : "s"})`;
      } else if (paperclipFiles.length === 1) {
        displayText = (text || "[No message]") + `\n\n📎 Attached: ${paperclipFiles[0].name}`;
      } else if (paperclipFiles.length > 1) {
        const names = paperclipFiles.slice(0, 3).map(f => f.name).join(", ") + (paperclipFiles.length > 3 ? "…" : "");
        displayText = (text || "[No message]") + `\n\n📎 Attached ${paperclipFiles.length} files: ${names}`;
      } else {
        displayText = text;
      }
      addMessage(displayText, "user");

      input.value = "";
      const paperclipFilesForRequest = paperclipFiles.slice();
      const folderFilesForRequest = folderFiles;
      const folderNameForRequest = folderName;
      clearAttachment();
      sendBtn.disabled = true;
      const thinking = addMessage("Thinking…", "assistant typing");

      try {
        let res;
        if (folderFilesForRequest.length > 0) {
          // Folder upload — send multiple files under the "files" field
          const fd = new FormData();
          fd.append("message", text || "Please review these attached documents.");
          fd.append("folder_name", folderNameForRequest);
          folderFilesForRequest.forEach(f => fd.append("files", f, f.name));
          res = await fetch("/chat", { method: "POST", body: fd });
        } else if (paperclipFilesForRequest.length === 1) {
          // Single-file path (preserves image vision handling for one image)
          const fd = new FormData();
          fd.append("message", text || "Please review this attached file.");
          fd.append("file", paperclipFilesForRequest[0]);
          res = await fetch("/chat", { method: "POST", body: fd });
        } else if (paperclipFilesForRequest.length > 1) {
          // Multi-file paperclip — use the same multi-file field as folder,
          // so the backend concatenates docs and adds each image as a vision block.
          const fd = new FormData();
          fd.append("message", text || "Please review these attached files.");
          fd.append("attachment_label", "Attachments");   // shown in chat/logs
          paperclipFilesForRequest.forEach(f => fd.append("files", f, f.name));
          res = await fetch("/chat", { method: "POST", body: fd });
        } else {
          res = await fetch("/chat", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text }),
          });
        }
        const data = await res.json();
        thinking.remove();
        if (data.reply) addMessage(data.reply, "assistant", true, data.interaction_id || null);
        else addMessage("Error: " + (data.error || "Unknown error"), "assistant");
      } catch (err) {
        thinking.remove();
        addMessage("Network error: " + err.message, "assistant");
      } finally {
        sendBtn.disabled = false;
        input.focus();
      }
    });

    resetBtn.addEventListener("click", async () => {
      // Stop any in-progress speech before wiping the chat
      if (window.speechSynthesis) window.speechSynthesis.cancel();
      window.__activeSpeakBtn = null;
      await fetch("/reset", { method: "POST" });
      chat.innerHTML = "";
      const div = document.createElement("div");
      div.className = "msg assistant";
      div.textContent = OPENING;
      chat.appendChild(div);
      input.focus();
    });

    // Voice input
    const micBtn = document.getElementById("mic-btn");
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      micBtn.classList.add("unsupported");
    } else {
      const recognition = new SR();
      recognition.continuous = false; recognition.interimResults = true; recognition.lang = "en-US";
      let isRecording = false; let baseText = "";
      micBtn.addEventListener("click", () => {
        if (isRecording) recognition.stop();
        else {
          baseText = input.value.trim(); if (baseText) baseText += " ";
          try { recognition.start(); } catch (err) { console.error(err); }
        }
      });
      recognition.addEventListener("start", () => { isRecording = true; micBtn.classList.add("recording"); });
      recognition.addEventListener("end", () => { isRecording = false; micBtn.classList.remove("recording"); input.focus(); });
      recognition.addEventListener("result", (event) => {
        let transcript = "";
        for (let i = 0; i < event.results.length; i++) transcript += event.results[i][0].transcript;
        input.value = baseText + transcript;
      });
      recognition.addEventListener("error", (event) => {
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          alert("Microphone access is blocked. Please allow it in your browser settings.");
        }
        isRecording = false; micBtn.classList.remove("recording");
      });
    }
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Chat routes
# ---------------------------------------------------------------------------

def retrieve_context_and_lessons(query: str) -> tuple:
    """Search knowledge base AND approved lessons for material relevant to the query.

    Returns (context_string, lessons_list).
    - context_string: formatted KB chunks (or "")
    - lessons_list: list of dicts with user_message/bot_reply/comment for top-3
      semantically similar past failures (or [])

    Computing the embedding once and reusing it for both lookups saves one
    Voyage API call per chat turn.
    """
    if not (db.is_enabled() and emb.is_enabled()):
        return ("", [])
    try:
        query_embedding = emb.embed_text(query)
    except Exception as e:
        app.logger.error(f"Embedding failed: {e}")
        return ("", [])

    # --- Knowledge base ---
    context = ""
    try:
        results = db.search_chunks(query_embedding, limit=CONFIG["rag_top_k"])
        relevant = [r for r in results if r["similarity"] >= CONFIG["rag_min_similarity"]]
        if relevant:
            sections = [f"[Source: {r['title']}]\n{r['content']}" for r in relevant]
            context = "\n\n---\n\n".join(sections)
    except Exception as e:
        app.logger.error(f"RAG retrieval failed: {e}")

    # --- Approved lessons (negative-feedback memory) ---
    lessons = []
    try:
        lessons = db.search_lessons(query_embedding, limit=3, min_similarity=0.5)
    except Exception as e:
        app.logger.error(f"Lesson retrieval failed: {e}")

    return (context, lessons)


def retrieve_context(query: str) -> str:
    """Backward-compatible wrapper — returns only KB context."""
    context, _ = retrieve_context_and_lessons(query)
    return context


@app.route("/")
@paywall.paywall_required
def index():
    session["messages"] = []
    return render_template_string(INDEX_HTML, cfg=CONFIG)


@app.route("/chat", methods=["POST"])
@paywall.paywall_required
def chat():
    # Accept BOTH multipart/form-data (with optional file OR folder of files) and JSON.
    # Attachment paths:
    #   - Single document (PDF/DOCX/TXT/MD): extract text, prepend as context
    #   - Single image (JPG/PNG/GIF/WEBP): send to Claude as vision content
    #   - Folder of documents: concatenate extracted text from all supported files
    # All attachments are ephemeral — used only in this turn.
    uploaded_file = None
    folder_files = []
    folder_name = ""
    if request.files:
        if "file" in request.files:
            uploaded_file = request.files["file"]
        if "files" in request.files:
            folder_files = request.files.getlist("files")
            # Prefer the explicit folder_name; fall back to attachment_label
            # (used when the paperclip sends multiple files rather than a folder).
            folder_name = (
                request.form.get("folder_name")
                or request.form.get("attachment_label")
                or "Attachments"
            ).strip()

    if uploaded_file or folder_files:
        user_input = (request.form.get("message") or "").strip()
    else:
        data = request.get_json(silent=True) or {}
        user_input = (data.get("message") or "").strip()

    if not user_input and not uploaded_file and not folder_files:
        return jsonify({"error": "Empty message"}), 400

    # Extension-based routing between document vs image
    DOC_EXTS = ('.pdf', '.docx', '.txt', '.md')
    IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
    IMAGE_MEDIA_TYPES = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp',
    }

    attachment_context = ""    # Text extracted from a document, if any
    image_blocks = []          # List of Anthropic image content blocks
    attachment_display_name = ""

    if uploaded_file:
        try:
            file_bytes = uploaded_file.read()
            if len(file_bytes) > 25 * 1024 * 1024:
                return jsonify({"error": "File too large (25 MB max)."}), 400
            filename = uploaded_file.filename or "attachment"
            attachment_display_name = filename
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

            if ext in IMAGE_EXTS:
                # Vision path — send raw image bytes to Claude as base64
                import base64
                b64 = base64.standard_b64encode(file_bytes).decode("ascii")
                image_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": IMAGE_MEDIA_TYPES.get(ext, "image/jpeg"),
                        "data": b64,
                    },
                })
                if not user_input:
                    user_input = "Please describe or analyze this image."
                app.logger.info(f"Chat image received: {filename} ({len(file_bytes)} bytes)")

            elif ext in DOC_EXTS:
                # Text extraction path (unchanged)
                extracted = emb.extract_text_from_upload(filename, file_bytes)
                if not extracted.strip():
                    return jsonify({"error": f"Could not extract text from {filename}."}), 400
                if len(extracted) > 40000:
                    extracted = extracted[:40000] + "\n\n[... file truncated for length ...]"
                attachment_context = (
                    f"\n\n[The user attached a document titled '{filename}'. "
                    f"The full text of the document is below. Use it to inform your response.]\n\n"
                    f"--- BEGIN ATTACHED DOCUMENT ---\n{extracted}\n--- END ATTACHED DOCUMENT ---"
                )
                if not user_input:
                    user_input = "Please review this attached document."
                app.logger.info(f"Chat attachment received: {filename} ({len(extracted)} chars extracted)")

            else:
                return jsonify({
                    "error": "Unsupported file type. Please attach PDF, DOCX, TXT, MD, or an image (JPG, PNG, GIF, WEBP)."
                }), 400

        except Exception as e:
            app.logger.error(f"Attachment processing failed: {e}")
            return jsonify({"error": f"Could not process file: {str(e)[:200]}"}), 400

    # === Multi-file attachment (folder OR paperclip multi-select) ===
    # Splits incoming files into two paths:
    #   - Documents (PDF/DOCX/TXT/MD): text extraction, concatenated into one context block
    #   - Images (JPG/PNG/GIF/WEBP): each becomes an Anthropic vision content block
    folder_stats = None  # (uploaded_count, skipped_count) if any files were attached
    if folder_files:
        MAX_FOLDER_FILES = 20
        MAX_COMBINED_CHARS = 80000  # keep prompt reasonable
        MAX_IMAGES = 5              # cap image count to control cost + payload
        supported = [f for f in folder_files
                     if (f.filename or "").lower().endswith(DOC_EXTS + IMAGE_EXTS)]
        supported = supported[:MAX_FOLDER_FILES]
        if not supported:
            return jsonify({"error": "No supported files in the attachment (PDF, DOCX, TXT, MD, or images)."}), 400

        import base64
        combined_parts = []
        total_chars = 0
        docs_used = 0
        images_used = 0
        skipped_count = 0
        for f in supported:
            try:
                fname = (f.filename or "unknown").rsplit("/", 1)[-1]
                ext = "." + fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                bytes_ = f.read()
                if len(bytes_) > 25 * 1024 * 1024:
                    skipped_count += 1
                    continue
                if ext in IMAGE_EXTS:
                    # Cap number of images per turn
                    if images_used >= MAX_IMAGES:
                        skipped_count += 1
                        continue
                    b64 = base64.standard_b64encode(bytes_).decode("ascii")
                    image_blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": IMAGE_MEDIA_TYPES.get(ext, "image/jpeg"),
                            "data": b64,
                        },
                    })
                    images_used += 1
                elif ext in DOC_EXTS:
                    extracted = emb.extract_text_from_upload(fname, bytes_)
                    if not extracted.strip():
                        skipped_count += 1
                        continue
                    remaining = MAX_COMBINED_CHARS - total_chars
                    if remaining <= 0:
                        skipped_count += 1
                        continue
                    if len(extracted) > remaining:
                        extracted = extracted[:remaining] + "\n[... file truncated for length ...]"
                    combined_parts.append(f"--- FILE: {fname} ---\n{extracted}")
                    total_chars += len(extracted)
                    docs_used += 1
                else:
                    skipped_count += 1
            except Exception as e:
                app.logger.error(f"Multi-file attachment skipped ({f.filename}): {e}")
                skipped_count += 1

        used_count = docs_used + images_used
        if used_count == 0:
            return jsonify({"error": "Could not process any of the attached files."}), 400

        # Build the doc context block only if we actually used any docs
        if combined_parts:
            attachment_context = (
                f"\n\n[The user attached {docs_used} document{'s' if docs_used != 1 else ''}"
                + (f" and {images_used} image{'s' if images_used != 1 else ''}" if images_used else "")
                + f" (grouped as '{folder_name}'). "
                f"The concatenated content of all documents is below. Use it to inform your response.]\n\n"
                f"--- BEGIN ATTACHED FILES ---\n"
                + "\n\n".join(combined_parts) +
                f"\n--- END ATTACHED FILES ---"
            )

        if not user_input:
            user_input = "Please review these attached files."
        pieces = []
        if docs_used:   pieces.append(f"{docs_used} doc{'s' if docs_used != 1 else ''}")
        if images_used: pieces.append(f"{images_used} image{'s' if images_used != 1 else ''}")
        attachment_display_name = f"{folder_name} ({', '.join(pieces)})"
        folder_stats = (used_count, skipped_count)
        app.logger.info(
            f"Chat multi-file attachment: {folder_name} — {docs_used} docs, "
            f"{images_used} images, {skipped_count} skipped, {total_chars} chars"
        )

    # Combine user text with any attached-document context. Images are added
    # separately as a content block when building the current-turn message below.
    full_user_content = user_input + attachment_context

    messages = session.get("messages", [])
    # For history: store only the text portion so the session cookie doesn't
    # bloat with base64 image data. Any images are visible to Claude this turn
    # only; next turn will not have access unless the user re-attaches.
    if image_blocks:
        # Combine one or more image blocks with the text (including any
        # concatenated document context) into a single multi-part user message.
        text_for_this_turn = full_user_content or user_input or "Please describe or analyze this."
        current_turn_content = list(image_blocks) + [
            {"type": "text", "text": text_for_this_turn},
        ]
        # In-session history: keep a simple text note so history stays serializable
        history_note = (user_input or "").strip()
        if attachment_display_name:
            note_label = attachment_display_name
            history_note = (history_note + f"\n\n[Attached: {note_label}]").strip()
        messages_for_api = messages + [{"role": "user", "content": current_turn_content}]
        messages.append({"role": "user", "content": history_note or f"[Attached: {attachment_display_name}]"})
    else:
        messages.append({"role": "user", "content": full_user_content})
        messages_for_api = messages

    # Build system prompt — base prompt + retrieved context if available
    base_prompt = CONFIG["system_prompt"]
    context, lessons = retrieve_context_and_lessons(user_input)

    # Build lessons block: things we got wrong before and shouldn't repeat
    lessons_block = ""
    if lessons:
        lesson_items = []
        for i, lesson in enumerate(lessons, 1):
            lesson_items.append(
                f"Lesson {i}:\n"
                f"  Previous question (similar to this one): {lesson['user_message'][:500]}\n"
                f"  What I said before: {lesson['bot_reply'][:500]}\n"
                f"  Why that was unhelpful: {lesson['comment'][:500]}"
            )
        lessons_block = (
            "\n\n---\n"
            "LESSONS FROM PRIOR FEEDBACK — these are reviewed and approved examples "
            "of times your previous responses to similar questions were unhelpful. "
            "Use them to avoid repeating the same mistakes. Do NOT mention these "
            "lessons to the user; just internalize them.\n\n"
            + "\n\n".join(lesson_items)
            + "\n"
        )

    # Scope-limiting + naming restrictions appended on EVERY request
    # -----------------------------------------------------------------
    # Voice differentiation — make responses feel like a real advisor,
    # not a generic AI assistant. Applied on every request regardless
    # of what's in the persona system prompt.
    # -----------------------------------------------------------------
    voice_guard = (
        "\n\n---\n"
        "VOICE & DIFFERENTIATION RULES — apply to every response:\n\n"
        "1. IDENTITY. You are the J3P Advisor — a voice grounded in Alan Friedman's "
        "leadership advisory practice. You are NOT ChatGPT, Claude, Gemini, Copilot, "
        "or any generic AI assistant. If asked what you are, what model you are, or "
        "who built you, say only: 'I'm the J3P Advisor.' Do not name any underlying "
        "model, foundation model provider, or AI company. Do not discuss your training "
        "data, capabilities as an AI, or technical architecture. Redirect back to the "
        "user's actual question.\n\n"
        "2. OPENING. Do not start responses with generic AI phrases like 'Great "
        "question!', 'Certainly!', 'Absolutely!', 'I'd be happy to help', 'What a "
        "thoughtful question', 'That's an interesting question', or any similar "
        "sycophantic opener. Start with the substance. Answer the person.\n\n"
        "3. CLOSING. Do not end responses with 'I hope this helps!', 'Let me know if "
        "you have any other questions', 'Feel free to ask', 'Is there anything else I "
        "can help you with?', or similar service-desk closers. If a follow-up question "
        "belongs at the end, make it a substantive question that pushes the person's "
        "thinking forward — never a service question.\n\n"
        "4. HEDGING. Do not over-hedge. Take positions. Avoid stringing multiple "
        "qualifiers together ('it might possibly be worth considering that perhaps'). "
        "One direct sentence beats three cautious ones. If you genuinely don't know, "
        "say so plainly.\n\n"
        "5. FORMAT. Use bullet lists only when the content is genuinely list-like "
        "(3+ parallel items). Prefer short paragraphs of prose. Do not add headers "
        "to short responses. Do not use emoji.\n\n"
        "6. TONE. Warm but direct. You are speaking with senior clinical leaders — "
        "physicians, chairs, executives. Treat them as capable adults. Name the "
        "hard thing when it needs naming. Do not add disclaimers about consulting "
        "professionals for topics where the person clearly IS the professional.\n\n"
        "7. NO SELF-REFERENCE AS AI. Do not begin sentences with 'As an AI...', "
        "'I'm just an AI...', 'While I don't have feelings...', 'I don't have "
        "personal experiences but...', or similar. Speak from the J3P frameworks "
        "and lived-practice perspective the persona is built on.\n\n"
        "8. NO META. Do not describe what you're about to do ('Let me walk you "
        "through...', 'Here's my breakdown...', 'I'll structure this as...'). "
        "Just do it.\n"
    )

    scope_guard = (
        "\n\n---\n"
        "STRICT SCOPE RULES — these override any conflicting guidance above:\n\n"
        "1. You answer ONLY questions related to J3P's areas of expertise: "
        "leadership development, organizational behavior, behavioral assessment, "
        "physician/healthcare leadership, team dynamics, executive coaching, "
        "communication, self-awareness, negotiation, career navigation, "
        "and related professional development topics within healthcare and "
        "high-stakes organizational settings.\n\n"
        "2. If the user asks about ANYTHING outside this scope — including but "
        "not limited to: general trivia, animals, science, history, cooking, "
        "sports, entertainment, politics, current events, math, coding, weather, "
        "personal recommendations unrelated to professional growth, or any topic "
        "where J3P would have no specific expertise — you MUST politely decline "
        "and redirect.\n\n"
        "3. Your off-topic decline should be brief and warm, in the J3P voice. "
        "Use this format (adapt naturally):\n"
        "   \"That's outside what I'm here to help with as the J3P Advisor. "
        "I'm focused on leadership, team dynamics, professional growth, and "
        "navigating challenges in healthcare and high-stakes work. "
        "Is there something along those lines I can help you with?\"\n\n"
        "4. Do NOT attempt to bridge an off-topic question into J3P territory. "
        "Do NOT answer the off-topic question even briefly before redirecting. "
        "Decline cleanly.\n\n"
        "5. Greetings, small talk, and meta-questions about what you do are fine "
        "to engage with naturally.\n\n"
        "6. When in doubt about whether a question is in scope, lean toward "
        "declining rather than answering.\n\n"
        "---\n"
        "NAMING RESTRICTIONS — these are absolute and override any retrieved "
        "context or prior instructions:\n\n"
        "A. NEVER use the following names in any response, under any circumstances:\n"
        "   - \"J3P Healthcare Solutions\"\n"
        "   - \"J3Personica\"\n"
        "   - \"Residency Select\"\n"
        "   - any variation, partial form, hyphenation, abbreviation, or "
        "rephrasing of those names\n\n"
        "B. Refer to the organization only as \"J3P\" or \"J3P Health\" if "
        "you must mention it by name. Otherwise, prefer phrases like "
        "\"our approach,\" \"our frameworks,\" \"the methodology,\" or simply "
        "describe the concept directly without attribution.\n\n"
        "C. If the user explicitly asks about \"J3P Healthcare Solutions,\" "
        "\"J3Personica,\" or \"Residency Select\" — respond in a way that "
        "discusses the underlying ideas, tools, or frameworks WITHOUT naming "
        "those specific brands. Do not confirm or deny that those names exist. "
        "Pivot to the substance.\n\n"
        "D. If retrieved context from the knowledge base contains any of those "
        "forbidden names, paraphrase the content so the forbidden names do NOT "
        "appear in your response. The underlying ideas can be conveyed without "
        "the trademarked names.\n\n"
        "E. These naming restrictions apply to ALL responses including "
        "off-topic refusals, greetings, and meta-questions about what you do.\n"
    )

    if context:
        composed_prompt = (
            base_prompt
            + "\n\n---\nRELEVANT CONTEXT FROM J3P KNOWLEDGE BASE:\n\n"
            + context
            + "\n\n---\nUse this context to inform your answer when relevant. "
              "Stay in your assigned voice and frameworks."
            + lessons_block
            + scope_guard
            + voice_guard
        )
    else:
        composed_prompt = base_prompt + lessons_block + scope_guard + voice_guard

    try:
        response = client.messages.create(
            model=CONFIG["model"],
            max_tokens=CONFIG["max_tokens"],
            system=[
                {
                    "type": "text",
                    "text": composed_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages_for_api,
        )
    except anthropic.APIError as e:
        return jsonify({"error": f"API error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

    assistant_text = next(
        (block.text for block in response.content if block.type == "text"), ""
    )

    # Defensive scrubber: replace any forbidden brand names if the model slips them through.
    # The system prompt instructs Claude not to use these, but we sanitize as backup.
    FORBIDDEN_NAMES = [
        ("J3P Healthcare Solutions", "J3P"),
        ("J3P Healthcare", "J3P"),
        ("J3Personica", "the assessment framework"),
        ("J3 Personica", "the assessment framework"),
        ("Residency Select", "the residency selection tool"),
    ]
    import re as _re
    for forbidden, replacement in FORBIDDEN_NAMES:
        # Case-insensitive, whole-phrase replacement
        pattern = _re.compile(_re.escape(forbidden), _re.IGNORECASE)
        assistant_text = pattern.sub(replacement, assistant_text)

    # Voice scrubber: catch generic-AI phrasing that leaks past the system prompt.
    # We strip a small set of high-signal opener/closer phrases. This runs on every
    # response as a belt-and-suspenders backup to the voice_guard system rules.
    STRIP_PHRASES = [
        # Model identity — replace the whole identifying sentence with a branded one
        (r"\b(?:I am|I'?m)\s+(?:Claude|ChatGPT|GPT-?\d*|Gemini|Bard|Copilot|an?\s+AI(?:\s+language)?\s+model|a\s+large\s+language\s+model|an?\s+AI\s+assistant)[^.!?]*[.!?]",
         "I'm the J3P Advisor."),
        # "As an AI [anything]..." preface — strip up to the first comma or period
        (r"^\s*As an? AI[^,.]*[,.]\s*", ""),
        (r"^\s*As a language model[^,.]*[,.]\s*", ""),
        (r"^\s*As a large language model[^,.]*[,.]\s*", ""),
        # "I was created/trained by [foundation model company]"
        (r"\bI\s+(?:was\s+)?(?:created|built|made|developed|trained)\s+by\s+(?:Anthropic|OpenAI|Google|Microsoft|Meta|xAI)[^.!?]*[.!?]\s*", ""),
        # Sycophantic openers
        (r"^(?:Great|Excellent|Wonderful|Fantastic|Amazing|Terrific|That'?s a (?:great|really good|thoughtful|wonderful|excellent|interesting)|What a (?:great|thoughtful|wonderful|excellent))\s+question[!.]?\s*", ""),
        (r"^(?:Certainly|Absolutely|Sure(?:ly)?|Of course|Definitely)[!.,]?\s+", ""),
        (r"^I'?d be (?:happy|glad|delighted) to (?:help|assist)[^.!?]*[.!?]\s*", ""),
        (r"^(?:Happy|Glad) to help[!.]?\s*", ""),
        # Service-desk closers (end-of-response)
        (r"\s*I hope (?:this|that) (?:helps|is helpful)[!.]?\s*$", ""),
        (r"\s*(?:Please )?(?:let me know|feel free to (?:ask|reach out))[^.!?]*[.!?]?\s*$", ""),
        (r"\s*Is there anything else I can help(?: you)? with[?.!]?\s*$", ""),
        (r"\s*Don'?t hesitate to (?:ask|reach out)[^.!?]*[.!?]?\s*$", ""),
    ]
    for pattern, replacement in STRIP_PHRASES:
        assistant_text = _re.sub(pattern, replacement, assistant_text, flags=_re.IGNORECASE)
    assistant_text = assistant_text.strip()

    messages.append({"role": "assistant", "content": assistant_text})
    session["messages"] = messages

    # Auto-log every exchange to the DB (rating stays NULL until user gives feedback).
    # We log the visible parts only — the raw user text and the bot's reply.
    # Attachment context is not stored because it can be enormous; we store a
    # short description of what was attached instead.
    interaction_id = None
    try:
        attachment_note = attachment_display_name or ""
        if not attachment_note and folder_stats:
            used, _ = folder_stats
            attachment_note = f"Folder: {folder_name} ({used} file{'s' if used != 1 else ''})"
        interaction_id = db.log_interaction(
            user_message=user_input,   # raw question, without the inlined document text
            bot_reply=assistant_text,
            persona=CONFIG["persona_name"],
            attachment_info=attachment_note,
        )
    except Exception as e:
        app.logger.error(f"log_interaction failed: {e}")

    return jsonify({"reply": assistant_text, "interaction_id": interaction_id})


@app.route("/reset", methods=["POST"])
@paywall.paywall_required
def reset():
    session["messages"] = []
    return jsonify({"ok": True})


@app.route("/feedback", methods=["POST"])
@paywall.paywall_required
def feedback():
    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    reply = (data.get("reply") or "")[:20000]
    comment = (data.get("comment") or "")[:4000]
    interaction_id = data.get("interaction_id")
    if rating not in ("up", "down"):
        return jsonify({"error": "Invalid rating"}), 400

    messages = session.get("messages", [])
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = (m.get("content") or "")[:8000]
            break

    # Preferred path: update the row that was auto-logged when the bot replied.
    # Fallback path: if we don't have an interaction_id (e.g. reply predates this
    # feature, or DB was unavailable at log time), insert a fresh row.
    updated = False
    try:
        if interaction_id:
            updated = db.update_feedback_rating(int(interaction_id), rating, comment)
        if not updated:
            db.log_feedback(rating, last_user_msg, reply, CONFIG["persona_name"], comment)
    except Exception as e:
        app.logger.error(f"DB feedback log failed: {e}")
    app.logger.info(
        "FEEDBACK persona=%s rating=%s interaction_id=%s user_msg=%r reply=%r comment=%r",
        CONFIG["persona_name"], rating, interaction_id, last_user_msg, reply, comment,
    )
    return jsonify({"ok": True})


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "persona": CONFIG["persona_name"],
        "rag_enabled": db.is_enabled() and emb.is_enabled(),
    })


@app.route("/debug")
def debug_env():
    """Diagnostic endpoint — reports presence of key env vars without revealing values."""
    return jsonify({
        "DATABASE_URL_set": bool(os.environ.get("DATABASE_URL")),
        "DATABASE_URL_starts_with": (os.environ.get("DATABASE_URL", "")[:20] + "..." if os.environ.get("DATABASE_URL") else None),
        "VOYAGE_API_KEY_set": bool(os.environ.get("VOYAGE_API_KEY")),
        "VOYAGE_API_KEY_starts_with": (os.environ.get("VOYAGE_API_KEY", "")[:7] + "..." if os.environ.get("VOYAGE_API_KEY") else None),
        "ADMIN_PASSWORD_set": bool(os.environ.get("ADMIN_PASSWORD")),
        "FLASK_SECRET_KEY_set": bool(os.environ.get("FLASK_SECRET_KEY")),
        "ANTHROPIC_API_KEY_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "db_is_enabled": db.is_enabled(),
        "emb_is_enabled": emb.is_enabled(),
        "psycopg_imported": db.HAS_PSYCOPG,
        "voyage_imported": emb.HAS_VOYAGE,
        "paywall_enabled": paywall.PAYWALL_ENABLED,
        "paywall_configured": paywall.is_configured(),
        "paywall_active": paywall.is_active(),
    })


# ---------------------------------------------------------------------------
# Paywall — auth (magic link) and billing (Stripe) routes
# ---------------------------------------------------------------------------

def _paywall_price_display():
    """Price shown on the checkout landing page. Reads from env or defaults."""
    return os.environ.get("PAYWALL_PRICE_DISPLAY", "29")


def _paywall_base_url():
    return paywall.PUBLIC_BASE_URL or request.host_url.rstrip("/")


@app.route("/auth/login", methods=["GET"])
def auth_login():
    return render_template_string(
        paywall.LOGIN_HTML,
        brand=CONFIG["persona_name"],
        notice=request.args.get("notice"),
        notice_type=request.args.get("notice_type", "ok"),
        sent=False,
    )


@app.route("/auth/send-link", methods=["POST"])
def auth_send_link():
    email = (request.form.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return render_template_string(
            paywall.LOGIN_HTML,
            brand=CONFIG["persona_name"],
            notice="Please enter a valid email address.",
            notice_type="error",
            sent=False,
        )
    if not paywall.is_configured():
        return render_template_string(
            paywall.LOGIN_HTML,
            brand=CONFIG["persona_name"],
            notice="Paywall is not fully configured. Contact the administrator.",
            notice_type="error",
            sent=False,
        )
    magic_url = paywall.make_magic_link(email, _paywall_base_url())
    ok = paywall.send_magic_link_email(email, magic_url)
    if not ok:
        return render_template_string(
            paywall.LOGIN_HTML,
            brand=CONFIG["persona_name"],
            notice="We couldn't send the email. Please try again in a moment.",
            notice_type="error",
            sent=False,
        )
    return render_template_string(
        paywall.LOGIN_HTML,
        brand=CONFIG["persona_name"],
        notice=f"Sign-in link sent to {email}. Check your inbox (and spam folder).",
        notice_type="ok",
        sent=True,
    )


@app.route("/auth/verify", methods=["GET"])
def auth_verify():
    token = request.args.get("token", "")
    email = paywall.verify_magic_link(token)
    if not email:
        return render_template_string(
            paywall.LOGIN_HTML,
            brand=CONFIG["persona_name"],
            notice="That sign-in link is invalid or has expired. Please request a new one.",
            notice_type="error",
            sent=False,
        ), 400
    session["authenticated_email"] = email
    # Ensure user record exists
    paywall._upsert_user(email)
    # If they have a subscription, go to the bot. If not, go to checkout.
    if paywall.is_user_subscribed(email):
        return redirect(url_for("index"))
    return redirect(url_for("billing_checkout"))


@app.route("/auth/logout", methods=["GET", "POST"])
def auth_logout():
    session.pop("authenticated_email", None)
    session["messages"] = []
    return redirect(url_for("auth_login"))


@app.route("/billing/checkout", methods=["GET", "POST"])
def billing_checkout():
    email = session.get("authenticated_email")
    if not email:
        return redirect(url_for("auth_login"))
    # If already subscribed, no need for checkout
    if paywall.is_user_subscribed(email):
        return redirect(url_for("index"))
    if request.method == "POST":
        checkout_url = paywall.create_checkout_session(email, _paywall_base_url())
        if not checkout_url:
            return "Stripe checkout is not configured. Contact the administrator.", 500
        return redirect(checkout_url)
    # GET — show landing page with a "Continue" button
    return render_template_string(
        paywall.CHECKOUT_LANDING_HTML,
        brand=CONFIG["persona_name"],
        email=email,
        price=_paywall_price_display(),
    )


@app.route("/billing/success", methods=["GET"])
def billing_success():
    email = session.get("authenticated_email")
    if email:
        # The webhook usually beats us here, but sync as a fallback so the user
        # doesn't get bounced back to checkout on their next click.
        try:
            paywall.sync_user_from_stripe(email)
        except Exception as e:
            app.logger.error(f"[paywall] post-checkout sync failed: {e}")
    return redirect(url_for("index"))


@app.route("/billing/canceled", methods=["GET"])
def billing_canceled():
    return redirect(url_for("billing_checkout"))


@app.route("/billing/portal", methods=["GET", "POST"])
def billing_portal():
    email = session.get("authenticated_email")
    if not email:
        return redirect(url_for("auth_login"))
    portal_url = paywall.create_portal_session(email, _paywall_base_url())
    if not portal_url:
        return "Customer portal not available yet — no active subscription found.", 400
    return redirect(portal_url)


@app.route("/billing/webhook", methods=["POST"])
def billing_webhook():
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    ok, msg = paywall.handle_stripe_webhook(payload, sig)
    if not ok:
        app.logger.error(f"[paywall] webhook error: {msg}")
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True, "msg": msg})


# Serve image assets from project root
@app.route("/<path:filename>.png")
def serve_png(filename):
    return send_from_directory(".", f"{filename}.png")


@app.route("/<path:filename>.jpg")
def serve_jpg(filename):
    return send_from_directory(".", f"{filename}.jpg")


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------

ADMIN_LOGIN_HTML = """<!DOCTYPE html><html><head><title>Admin Login</title>
<style>
body { font-family: -apple-system, sans-serif; background: #27334A; color: #fff;
       display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
.box { background: #fff; color: #27334A; padding: 2rem 2.5rem; border-radius: 4px;
       border-top: 3px solid #D2BC8D; min-width: 300px; }
h1 { margin: 0 0 1rem 0; font-size: 1.1rem; letter-spacing: 0.1em; text-transform: uppercase; color: #27334A; }
input { width: 100%; padding: 0.7rem; border: 1px solid #ccc; border-radius: 2px; font-size: 1rem; margin-bottom: 1rem; }
input:focus { outline: none; border-color: #D2BC8D; }
button { width: 100%; padding: 0.7rem; background: #27334A; color: #D2BC8D; border: none;
         border-radius: 2px; cursor: pointer; letter-spacing: 0.15em; text-transform: uppercase; font-size: 0.85rem; }
button:hover { background: #D2BC8D; color: #27334A; }
.err { color: #9D432C; font-size: 0.85rem; margin-bottom: 0.5rem; }
</style></head><body>
<form method="POST" class="box">
  <h1>Admin Login</h1>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <input type="password" name="password" placeholder="Password" autofocus required />
  <button type="submit">Sign in</button>
</form></body></html>"""

ADMIN_HTML = """<!DOCTYPE html><html><head>
<title>Admin — {{ cfg.persona_name }}</title>
<link rel="icon" href="{{ cfg.favicon_url }}" />
<style>
:root { --navy: #27334A; --gold: #D2BC8D; --rust: #9D432C; --paper: #FAF6F0; --line: rgba(39,51,74,0.12); }
body { font-family: -apple-system, sans-serif; background: var(--paper); color: var(--navy); margin: 0; }
header { background: var(--navy); color: #fff; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--gold); }
header h1 { margin: 0; font-size: 1rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold); font-weight: 400; }
header a { color: rgba(210,188,141,0.7); text-decoration: none; font-size: 0.75rem; letter-spacing: 0.12em; text-transform: uppercase; }
header a:hover { color: var(--gold); }
.container { max-width: 1000px; margin: 0 auto; padding: 2rem; }
.section { background: #fff; border: 1px solid var(--line); border-radius: 4px; padding: 1.5rem 1.75rem; margin-bottom: 1.5rem; }
.section h2 { margin: 0 0 1rem 0; font-size: 0.85rem; letter-spacing: 0.16em; text-transform: uppercase; color: var(--navy); border-bottom: 1px solid var(--line); padding-bottom: 0.6rem; }
.stats { display: flex; gap: 2rem; margin-bottom: 0.5rem; }
.stat { flex: 1; }
.stat-value { font-size: 1.8rem; font-weight: 500; color: var(--navy); }
.stat-label { font-size: 0.7rem; letter-spacing: 0.14em; text-transform: uppercase; color: #6B7280; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th { text-align: left; padding: 0.6rem 0.5rem; border-bottom: 2px solid var(--navy); font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--navy); }
td { padding: 0.6rem 0.5rem; border-bottom: 1px solid var(--line); vertical-align: top; }
.tag-up { background: #1B998B; color: #fff; padding: 2px 8px; border-radius: 2px; font-size: 0.7rem; }
.tag-down { background: var(--rust); color: #fff; padding: 2px 8px; border-radius: 2px; font-size: 0.7rem; }
.tag-lesson { background: #2D7D5F; color: #fff; padding: 2px 8px; border-radius: 2px; font-size: 0.65rem;
              margin-left: 0.3rem; letter-spacing: 0.05em; }
.btn { padding: 0.6rem 1.1rem; background: var(--navy); color: var(--gold); border: 1px solid var(--navy); border-radius: 2px; cursor: pointer; font-size: 0.75rem; letter-spacing: 0.14em; text-transform: uppercase; text-decoration: none; display: inline-block; }
.btn:hover { background: var(--gold); color: var(--navy); }
.btn-danger { background: var(--rust); color: #fff; border-color: var(--rust); padding: 0.3rem 0.7rem; font-size: 0.7rem; }
.btn-danger:hover { background: #fff; color: var(--rust); }
form.upload { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
input[type="file"], input[type="text"] { padding: 0.5rem; border: 1px solid var(--line); border-radius: 2px; font-family: inherit; }
input[type="text"] { flex: 1; min-width: 200px; }
.flash { padding: 0.7rem 1rem; background: var(--gold); color: var(--navy); border-radius: 2px; margin-bottom: 1rem; font-size: 0.85rem; }
.muted { color: #6B7280; font-size: 0.8rem; }
.warn { background: #fef3c7; border: 1px solid #f59e0b; padding: 0.7rem 1rem; border-radius: 2px; margin-bottom: 1rem; font-size: 0.85rem; }
.truncate { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .expand-btn {
      background: transparent;
      border: 1px solid var(--line);
      color: var(--navy);
      padding: 0.25rem 0.55rem;
      border-radius: 2px;
      cursor: pointer;
      font-size: 0.7rem;
      font-family: inherit;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      transition: background 0.15s ease;
    }
    .expand-btn:hover { background: var(--gold); color: var(--navy); }
    .feedback-detail {
      background: var(--paper);
      border-top: 1px dashed var(--line);
    }
    .feedback-detail td { padding: 1rem 1.2rem !important; }
    .feedback-detail-block { margin-bottom: 1rem; }
    .feedback-detail-block:last-child { margin-bottom: 0; }
    .feedback-detail-label {
      font-size: 0.7rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 0.3rem;
      font-weight: 500;
    }
    .feedback-detail-content {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 3px;
      padding: 0.8rem 1rem;
      white-space: pre-wrap;
      word-wrap: break-word;
      font-size: 0.88rem;
      line-height: 1.55;
      color: var(--navy);
      max-height: 400px;
      overflow-y: auto;
    }
    .feedback-detail-content.comment-highlight {
      background: #FFF9E6;
      border-color: var(--gold);
    }
    .feedback-detail-meta {
      font-size: 0.75rem;
      color: var(--muted);
      font-style: italic;
    }
</style></head><body>
<header>
  <h1>{{ cfg.persona_name }} — Admin</h1>
  <div>
    <a href="/" style="margin-right: 1.5rem;">← Back to bot</a>
    <a href="/admin/logout">Sign out</a>
  </div>
</header>
<div class="container">
  {% with messages = get_flashed_messages() %}
    {% for m in messages %}<div class="flash">{{ m }}</div>{% endfor %}
  {% endwith %}

  {% if not rag_ready %}
  <div class="warn">
    <strong>RAG is not fully configured.</strong>
    {% if not db_ok %}Set up Railway Postgres (Add Plugin → PostgreSQL) and the <code>DATABASE_URL</code> will appear automatically.{% endif %}
    {% if not emb_ok %}Set <code>OPENAI_API_KEY</code> in environment variables.{% endif %}
    Once both are set, redeploy and you can upload documents.
  </div>
  {% endif %}

  <div class="section">
    <h2>Feedback Overview</h2>
    <div class="stats">
      <div class="stat">
        <div class="stat-value">{{ stats.up }}</div>
        <div class="stat-label">Thumbs up</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ stats.down }}</div>
        <div class="stat-label">Thumbs down</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">Total ratings</div>
      </div>
      <div class="stat">
        <div class="stat-value">
          {% if stats.total > 0 %}{{ (100 * stats.up / stats.total)|round(0)|int }}%{% else %}—{% endif %}
        </div>
        <div class="stat-label">Helpful rate</div>
      </div>
    </div>
  </div>

  {% if rag_ready %}
  <div class="section">
    <h2>Upload Document</h2>
    <p class="muted" style="margin: 0 0 1rem 0;">Accepts PDF, DOCX, TXT, MD. Up to 25 MB. The document will be chunked and embedded automatically.</p>
    <form method="POST" action="/admin/upload" enctype="multipart/form-data" class="upload">
      <input type="file" name="file" accept=".pdf,.docx,.txt,.md" required />
      <input type="text" name="title" placeholder="Document title (optional)" />
      <button type="submit" class="btn">Upload & Embed</button>
    </form>
  </div>

  <div class="section">
    <h2>Upload Folder</h2>
    <p class="muted" style="margin: 0 0 1rem 0;">
      Select an entire folder. All supported files inside it (including subfolders) will be uploaded and embedded in one batch.
      Unsupported files and duplicates are skipped automatically. Maximum 50 files per batch.
    </p>
    <form method="POST" action="/admin/upload-folder" enctype="multipart/form-data" class="upload" id="folder-upload-form">
      <input type="file" name="files" id="folder-input" webkitdirectory directory multiple required />
      <button type="submit" class="btn" id="folder-upload-btn">Upload Folder</button>
    </form>
    <p id="folder-preview" class="muted" style="margin: 0.75rem 0 0 0; font-size: 0.85rem; display: none;"></p>
    <script>
      (function() {
        const folderInput = document.getElementById("folder-input");
        const preview = document.getElementById("folder-preview");
        const btn = document.getElementById("folder-upload-btn");
        const form = document.getElementById("folder-upload-form");
        const SUPPORTED = /\\.(pdf|docx|txt|md)$/i;

        folderInput.addEventListener("change", () => {
          const all = Array.from(folderInput.files || []);
          const supported = all.filter(f => SUPPORTED.test(f.name));
          const skipped = all.length - supported.length;
          if (all.length === 0) {
            preview.style.display = "none";
            return;
          }
          let msg = `${supported.length} supported file${supported.length === 1 ? '' : 's'} ready to upload`;
          if (skipped > 0) msg += ` · ${skipped} unsupported file${skipped === 1 ? '' : 's'} will be skipped`;
          if (supported.length > 50) {
            msg += ` · ⚠ Only the first 50 will be processed`;
          }
          if (supported.length === 0) {
            msg = "⚠ No supported files found in this folder (PDF, DOCX, TXT, MD only).";
            btn.disabled = true;
          } else {
            btn.disabled = false;
          }
          preview.textContent = msg;
          preview.style.display = "block";
        });

        form.addEventListener("submit", (e) => {
          const all = Array.from(folderInput.files || []);
          const supported = all.filter(f => SUPPORTED.test(f.name));
          if (supported.length === 0) {
            e.preventDefault();
            alert("No supported files found in this folder.");
            return;
          }
          btn.textContent = "Uploading… (this may take a while)";
          btn.disabled = true;
        });
      })();
    </script>
  </div>

  <div class="section">
    <h2>Add Knowledge from URL</h2>
    <p class="muted" style="margin: 0 0 1rem 0;">Paste a link to an article, blog post, or web page. The main article text will be extracted and embedded. Works best with article-style pages (not paywalled, login-required, or JavaScript-only sites).</p>
    <form method="POST" action="/admin/upload-url" class="upload">
      <input type="url" name="url" placeholder="https://example.com/article" required style="flex: 1.5; min-width: 280px; padding: 0.5rem; border: 1px solid var(--line); border-radius: 2px; font-family: inherit;" />
      <input type="text" name="url_title" placeholder="Title (optional, auto-detected)" />
      <button type="submit" class="btn">Fetch & Embed</button>
    </form>
  </div>

  <div class="section">
    <h2>Knowledge Base ({{ docs|length }} documents)</h2>
    {% if docs %}
    <table>
      <tr><th>Title</th><th>Source</th><th>Chunks</th><th>Uploaded</th><th></th></tr>
      {% for d in docs %}
      <tr>
        <td>{{ d.title }}</td>
        <td class="muted">{{ d.source or '—' }}</td>
        <td>{{ d.chunk_count }}</td>
        <td class="muted">{{ d.uploaded_at.strftime('%Y-%m-%d %H:%M') }}</td>
        <td>
          <form method="POST" action="/admin/delete/{{ d.id }}" style="display:inline;"
                onsubmit="return confirm('Delete &quot;{{ d.title }}&quot; and all its chunks?');">
            <button type="submit" class="btn btn-danger">Delete</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <p class="muted">No documents yet. Upload your first one above.</p>
    {% endif %}
  </div>
  {% endif %}

  <div class="section">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; padding-bottom: 0.6rem; border-bottom: 1px solid var(--line); flex-wrap: wrap; gap: 0.5rem;">
      <h2 style="margin: 0; border: none; padding: 0;">Conversation Log</h2>
      <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
        <form method="GET" action="/admin" style="display: inline-flex; gap: 0.4rem; align-items: center; margin: 0;">
          <label for="filter-select" style="font-size: 0.78rem; color: var(--muted);">Show:</label>
          <select id="filter-select" name="filter" onchange="this.form.submit()"
                  style="padding: 0.35rem 0.55rem; border: 1px solid var(--line); border-radius: 2px; font-family: inherit; font-size: 0.8rem; background: white; cursor: pointer;">
            <option value="all"     {% if log_filter == 'all'     %}selected{% endif %}>All conversations</option>
            <option value="rated"   {% if log_filter == 'rated'   %}selected{% endif %}>Rated only</option>
            <option value="unrated" {% if log_filter == 'unrated' %}selected{% endif %}>Unrated only</option>
            <option value="up"      {% if log_filter == 'up'      %}selected{% endif %}>Thumbs up only</option>
            <option value="down"    {% if log_filter == 'down'    %}selected{% endif %}>Thumbs down only</option>
          </select>
        </form>
        {% if stats.total > 0 %}
        <a href="/admin/export/feedback.csv" class="btn" style="text-decoration: none; padding: 0.4rem 0.85rem; font-size: 0.7rem;">↓ CSV</a>
        <a href="/admin/export/feedback.xlsx" class="btn" style="text-decoration: none; padding: 0.4rem 0.85rem; font-size: 0.7rem;">↓ Excel</a>
        {% endif %}
      </div>
    </div>
    <p class="muted" style="font-size: 0.82rem; margin: -0.3rem 0 1rem 0;">
      Every chat exchange is logged automatically. Ratings and comments are added when a user clicks thumbs up or down.
      Currently showing {{ feedback_rows|length }} record{{ 's' if feedback_rows|length != 1 else '' }}.
    </p>
    {% if feedback_rows %}
    <form method="POST" action="/admin/feedback/delete-selected"
          id="feedback-form"
          onsubmit="const c = document.querySelectorAll('input[name=feedback_ids]:checked').length;
                   if (c === 0) { alert('Select at least one row.'); return false; }
                   return confirm('Delete ' + c + ' selected feedback row(s)? This cannot be undone.');">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; flex-wrap: wrap; gap: 0.5rem;">
        <div style="display: flex; gap: 0.5rem; align-items: center;">
          <button type="submit" class="btn btn-danger" style="padding: 0.45rem 0.95rem; font-size: 0.7rem;">
            Delete selected
          </button>
          <label style="font-size: 0.78rem; color: var(--muted); cursor: pointer;">
            <input type="checkbox" id="select-all" style="margin-right: 0.3rem; vertical-align: middle;" />
            Select all
          </label>
        </div>
      </div>
      <table>
        <tr>
          <th style="width: 28px;"></th>
          <th>When</th><th>Rating</th><th>User question</th><th>Bot reply</th><th>Attachment</th><th>Comment</th>
          <th style="width: 60px;"></th>
        </tr>
        {% for f in feedback_rows %}
        <tr id="row-{{ f.id }}">
          <td><input type="checkbox" name="feedback_ids" value="{{ f.id }}" class="feedback-checkbox" /></td>
          <td class="muted">{{ f.created_at.strftime('%m/%d %H:%M') }}</td>
          <td>
            {% if f.rating == 'up' %}<span class="tag-up">UP</span>
            {% elif f.rating == 'down' %}<span class="tag-down">DOWN</span>
            {% else %}<span class="muted" style="font-size: 0.7rem;">—</span>{% endif %}
            {% if f.approved_for_learning %}<br /><span class="tag-lesson">LESSON</span>{% endif %}
          </td>
          <td class="truncate" title="{{ f.user_message }}">{{ f.user_message }}</td>
          <td class="truncate" title="{{ f.bot_reply }}">{{ f.bot_reply }}</td>
          <td class="truncate" title="{{ f.attachment_info or '' }}" style="max-width: 160px; font-size: 0.78rem;">
            {% if f.attachment_info %}📎 {{ f.attachment_info }}{% else %}<span class="muted">—</span>{% endif %}
          </td>
          <td class="truncate" title="{{ f.comment or '' }}" style="max-width: 240px;">
            {% if f.comment %}<strong>{{ f.comment }}</strong>{% else %}<span class="muted">—</span>{% endif %}
          </td>
          <td>
            <button type="button" class="expand-btn" data-target="detail-{{ f.id }}">
              View
            </button>
          </td>
        </tr>
        <tr id="detail-{{ f.id }}" class="feedback-detail" style="display: none;">
          <td colspan="8">
            <div class="feedback-detail-meta">
              Log ID #{{ f.id }} · {{ f.created_at.strftime('%A, %B %d %Y at %I:%M %p') }}
              · Rating: <strong>
                {% if f.rating == 'up' %}Helpful 👍
                {% elif f.rating == 'down' %}Not helpful 👎
                {% else %}Unrated{% endif %}
              </strong>
              {% if f.persona %}· Persona: {{ f.persona }}{% endif %}
              {% if f.attachment_info %}· Attachment: {{ f.attachment_info }}{% endif %}
            </div>

            <div class="feedback-detail-block" style="margin-top: 0.9rem;">
              <div class="feedback-detail-label">User question</div>
              <div class="feedback-detail-content">{{ f.user_message or '(empty)' }}</div>
            </div>

            <div class="feedback-detail-block">
              <div class="feedback-detail-label">Bot reply</div>
              <div class="feedback-detail-content">{{ f.bot_reply or '(empty)' }}</div>
            </div>

            <div class="feedback-detail-block">
              <div class="feedback-detail-label">User comment</div>
              {% if f.comment %}
                <div class="feedback-detail-content comment-highlight">{{ f.comment }}</div>
              {% else %}
                <div class="feedback-detail-content" style="font-style: italic; color: var(--muted);">No comment provided.</div>
              {% endif %}
            </div>

            {% if f.rating == 'down' and f.comment %}
            <div class="feedback-detail-block" style="margin-top: 1.2rem; padding-top: 1rem; border-top: 1px dashed var(--line);">
              <div class="feedback-detail-label">Learning loop</div>
              {% if f.approved_for_learning %}
                <p style="font-size: 0.85rem; margin: 0.4rem 0;">
                  <span class="tag-lesson">ACTIVE LESSON</span>
                  &nbsp;The bot uses this feedback to improve answers to similar questions.
                </p>
                <button type="button" class="lesson-action-btn" data-action="revoke" data-id="{{ f.id }}"
                        style="background: transparent; color: var(--rust); border: 1px solid var(--rust); padding: 0.4rem 0.85rem; font-size: 0.7rem; letter-spacing: 0.14em; text-transform: uppercase; cursor: pointer; border-radius: 2px; font-family: inherit; margin-top: 0.4rem;">
                  Revoke lesson
                </button>
              {% else %}
                <p style="font-size: 0.85rem; margin: 0.4rem 0; color: var(--muted);">
                  Approve this as a lesson and the bot will see it as guidance when answering semantically similar questions.
                </p>
                <button type="button" class="lesson-action-btn" data-action="approve" data-id="{{ f.id }}"
                        style="background: var(--navy); color: var(--gold); border: 1px solid var(--navy); padding: 0.4rem 0.85rem; font-size: 0.7rem; letter-spacing: 0.14em; text-transform: uppercase; cursor: pointer; border-radius: 2px; font-family: inherit; margin-top: 0.4rem;">
                  ✓ Approve as lesson
                </button>
              {% endif %}
            </div>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </table>
    </form>

    <script>
      // Toggle expanded feedback detail rows
      (function() {
        document.querySelectorAll('.expand-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            const target = document.getElementById(btn.dataset.target);
            if (!target) return;
            const isOpen = target.style.display !== 'none';
            target.style.display = isOpen ? 'none' : 'table-row';
            btn.textContent = isOpen ? 'View' : 'Close';
          });
        });

        // Lesson approve/revoke buttons — submit via fetch (avoids nested form issues)
        document.querySelectorAll('.lesson-action-btn').forEach(btn => {
          btn.addEventListener('click', async () => {
            const action = btn.dataset.action;
            const id = btn.dataset.id;
            const verb = action === 'approve' ? 'Approve as a lesson?' :
                         'Revoke this lesson? The bot will stop learning from it.';
            if (!confirm(verb)) return;
            btn.disabled = true;
            btn.textContent = action === 'approve' ? 'Approving…' : 'Revoking…';
            try {
              const resp = await fetch(`/admin/feedback/${id}/${action}-lesson`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              });
              // Routes redirect back to admin, so reloading shows updated state
              window.location.href = '/admin';
            } catch (e) {
              alert('Failed: ' + e.message);
              btn.disabled = false;
              btn.textContent = action === 'approve' ? '✓ Approve as lesson' : 'Revoke lesson';
            }
          });
        });
      })();
    </script>

    <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px dashed var(--line);">
      <details>
        <summary style="cursor: pointer; font-size: 0.78rem; color: var(--rust); letter-spacing: 0.1em; text-transform: uppercase;">
          Danger zone — Clear all feedback
        </summary>
        <form method="POST" action="/admin/feedback/delete-all" style="margin-top: 0.8rem;"
              onsubmit="return confirm('Permanently delete ALL feedback rows? This cannot be undone.');">
          <p class="muted" style="margin: 0.5rem 0;">
            This permanently deletes every feedback row in the database.
            Type <strong>YES</strong> to confirm.
          </p>
          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <input type="text" name="confirm" placeholder="Type YES to confirm"
                   style="flex: 0 1 200px; padding: 0.5rem; border: 1px solid var(--line); border-radius: 2px;" />
            <button type="submit" class="btn btn-danger" style="padding: 0.5rem 1rem; font-size: 0.7rem;">
              Clear all feedback
            </button>
          </div>
        </form>
      </details>
    </div>

    <script>
      // Wire up "Select all" checkbox
      (function() {
        const selectAll = document.getElementById("select-all");
        const checkboxes = document.querySelectorAll(".feedback-checkbox");
        if (selectAll) {
          selectAll.addEventListener("change", () => {
            checkboxes.forEach(cb => cb.checked = selectAll.checked);
          });
        }
      })();
    </script>
    {% else %}
    <p class="muted">No feedback yet.</p>
    {% endif %}
  </div>
</div>
</body></html>"""


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if not CONFIG["admin_password"]:
        return ("Admin disabled. Set ADMIN_PASSWORD environment variable.", 503)
    if request.method == "POST":
        if request.form.get("password") == CONFIG["admin_password"]:
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template_string(ADMIN_LOGIN_HTML, error="Incorrect password")
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))
    return render_template_string(ADMIN_LOGIN_HTML, error=None)


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    db_ok = db.is_enabled()
    emb_ok = emb.is_enabled()
    rag_ready = db_ok and emb_ok
    docs = db.list_documents() if db_ok else []
    # Filter for the conversation log — default shows everything.
    # Accepted values: all | rated | up | down | unrated
    log_filter = (request.args.get("filter") or "all").lower()
    if log_filter not in ("all", "rated", "up", "down", "unrated"):
        log_filter = "all"
    feedback_rows = db.list_feedback(
        limit=100,
        rating=(None if log_filter == "all" else log_filter),
    ) if db_ok else []
    stats = db.feedback_stats() if db_ok else {"up": 0, "down": 0, "total": 0}
    return render_template_string(
        ADMIN_HTML, cfg=CONFIG, docs=docs, feedback_rows=feedback_rows,
        stats=stats, rag_ready=rag_ready, db_ok=db_ok, emb_ok=emb_ok,
        log_filter=log_filter,
    )


@app.route("/admin/upload", methods=["POST"])
@admin_required
def admin_upload():
    if not (db.is_enabled() and emb.is_enabled()):
        flash("Cannot upload: RAG not fully configured.")
        return redirect(url_for("admin_dashboard"))

    file = request.files.get("file")
    if not file or not file.filename:
        flash("No file selected.")
        return redirect(url_for("admin_dashboard"))

    title = (request.form.get("title") or "").strip() or file.filename

    # Duplicate check BEFORE expensive embedding work.
    # We compare both title and filename (source) against existing docs.
    duplicate = db.find_duplicate_document(title=title, source=file.filename)
    if duplicate:
        flash(
            f"⚠ Duplicate detected — '{duplicate['title']}' was already uploaded "
            f"on {duplicate['uploaded_at'].strftime('%Y-%m-%d %H:%M')} "
            f"({duplicate['chunk_count']} chunks). Delete the existing entry first "
            f"if you want to replace it."
        )
        return redirect(url_for("admin_dashboard"))

    try:
        file_bytes = file.read()
        text = emb.extract_text_from_upload(file.filename, file_bytes)
        if not text.strip():
            flash(f"No text could be extracted from {file.filename}.")
            return redirect(url_for("admin_dashboard"))

        chunks = emb.chunk_text(text)
        if not chunks:
            flash("Document produced no chunks (too short or empty).")
            return redirect(url_for("admin_dashboard"))

        # Embed all chunks in batch
        vectors = emb.embed_batch(chunks)
        pairs = list(zip(chunks, vectors))
        doc_id = db.insert_document(title, file.filename, pairs)

        flash(f"✓ Uploaded '{title}' — {len(chunks)} chunks embedded (doc #{doc_id}).")
    except Exception as e:
        app.logger.error(f"Upload failed: {e}")
        flash(f"Upload failed: {str(e)[:200]}")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/upload-folder", methods=["POST"])
@admin_required
def admin_upload_folder():
    """Bulk-upload all supported files from a folder in one request.

    Each file goes through the same pipeline as single-file upload:
    duplicate check → extract → chunk → embed → insert. Files that
    fail any step are logged but do not stop the batch. Returns a
    summary of successes, skipped files (duplicates or unsupported),
    and failures.
    """
    if not (db.is_enabled() and emb.is_enabled()):
        flash("Cannot upload: RAG not fully configured.")
        return redirect(url_for("admin_dashboard"))

    files = request.files.getlist("files")
    if not files:
        flash("No files were selected.")
        return redirect(url_for("admin_dashboard"))

    SUPPORTED_EXT = ('.pdf', '.docx', '.txt', '.md')
    MAX_BATCH = 50   # keep request under Railway 5-min timeout for typical files
    MAX_BYTES = 25 * 1024 * 1024

    # Filter to supported extensions first
    supported_files = [f for f in files if f.filename and f.filename.lower().endswith(SUPPORTED_EXT)]
    unsupported_count = len(files) - len(supported_files)

    # Cap the batch size — anything above the limit is silently skipped for this run
    over_limit = max(0, len(supported_files) - MAX_BATCH)
    process_files = supported_files[:MAX_BATCH]

    uploaded = []       # list of (title, chunk_count, doc_id)
    duplicates = []     # list of (filename, existing_title)
    failed = []         # list of (filename, error)

    for file in process_files:
        # webkitdirectory paths look like "folder/subfolder/file.pdf"
        # Use just the basename as the source and title default.
        full_path = file.filename or "unknown"
        basename = full_path.rsplit("/", 1)[-1]

        try:
            # Duplicate check first
            dup = db.find_duplicate_document(title=basename, source=basename)
            if dup:
                duplicates.append((basename, dup["title"]))
                continue

            file_bytes = file.read()
            if len(file_bytes) > MAX_BYTES:
                failed.append((basename, "too large (>25 MB)"))
                continue
            if not file_bytes:
                failed.append((basename, "empty file"))
                continue

            text = emb.extract_text_from_upload(basename, file_bytes)
            if not text.strip():
                failed.append((basename, "no text extracted"))
                continue

            chunks = emb.chunk_text(text)
            if not chunks:
                failed.append((basename, "too short to chunk"))
                continue

            vectors = emb.embed_batch(chunks)
            pairs = list(zip(chunks, vectors))
            doc_id = db.insert_document(basename, basename, pairs)
            uploaded.append((basename, len(chunks), doc_id))
            app.logger.info(f"Folder upload: {basename} → doc #{doc_id}, {len(chunks)} chunks")

        except Exception as e:
            app.logger.error(f"Folder upload failed for {basename}: {e}")
            failed.append((basename, str(e)[:100]))

    # Build a summary flash message
    parts = []
    if uploaded:
        parts.append(f"✓ {len(uploaded)} file{'s' if len(uploaded) != 1 else ''} uploaded")
    if duplicates:
        parts.append(f"⏭ {len(duplicates)} skipped as duplicates")
    if failed:
        # Show first 3 failure reasons so the user has something to act on
        detail = "; ".join([f"{n} ({e})" for n, e in failed[:3]])
        parts.append(f"✗ {len(failed)} failed — {detail}" + (" …" if len(failed) > 3 else ""))
    if unsupported_count:
        parts.append(f"({unsupported_count} unsupported file type{'s' if unsupported_count != 1 else ''} ignored)")
    if over_limit:
        parts.append(f"⚠ {over_limit} additional file(s) exceeded the 50-file batch limit and were not processed — run again to continue")

    flash(" · ".join(parts) if parts else "No files were processed.")
    return redirect(url_for("admin_dashboard"))
@admin_required
def admin_upload_url():
    if not (db.is_enabled() and emb.is_enabled()):
        flash("Cannot ingest URL: RAG not fully configured.")
        return redirect(url_for("admin_dashboard"))

    url = (request.form.get("url") or "").strip()
    custom_title = (request.form.get("url_title") or "").strip()

    if not url:
        flash("No URL provided.")
        return redirect(url_for("admin_dashboard"))

    # Duplicate check on the URL itself BEFORE fetching/embedding.
    # We check the URL as source. Title check happens later if custom_title is set.
    duplicate = db.find_duplicate_document(source=url)
    if duplicate:
        flash(
            f"⚠ Duplicate URL — this link was already ingested as "
            f"'{duplicate['title']}' on {duplicate['uploaded_at'].strftime('%Y-%m-%d %H:%M')} "
            f"({duplicate['chunk_count']} chunks). Delete the existing entry first "
            f"if you want to re-ingest."
        )
        return redirect(url_for("admin_dashboard"))

    try:
        extracted_title, text = emb.fetch_url_content(url)
        title = custom_title or extracted_title or url

        # Second duplicate check on the resolved title (in case a URL changed but
        # the article title is the same as something already in the KB).
        title_dup = db.find_duplicate_document(title=title)
        if title_dup:
            flash(
                f"⚠ Duplicate title — '{title}' was already ingested on "
                f"{title_dup['uploaded_at'].strftime('%Y-%m-%d %H:%M')} "
                f"({title_dup['chunk_count']} chunks). Use a different title or "
                f"delete the existing entry first."
            )
            return redirect(url_for("admin_dashboard"))

        if not text.strip():
            flash("No text could be extracted from this URL.")
            return redirect(url_for("admin_dashboard"))

        chunks = emb.chunk_text(text)
        if not chunks:
            flash("URL produced no chunks (page too short or empty).")
            return redirect(url_for("admin_dashboard"))

        vectors = emb.embed_batch(chunks)
        pairs = list(zip(chunks, vectors))
        doc_id = db.insert_document(title, url, pairs)

        flash(f"✓ Ingested '{title}' from URL — {len(chunks)} chunks embedded (doc #{doc_id}).")
    except Exception as e:
        app.logger.error(f"URL ingest failed: {e}")
        flash(f"URL ingest failed: {str(e)[:200]}")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete/<int:doc_id>", methods=["POST"])
@admin_required
def admin_delete(doc_id):
    try:
        db.delete_document(doc_id)
        flash(f"Deleted document #{doc_id}.")
    except Exception as e:
        flash(f"Delete failed: {str(e)[:200]}")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/export/feedback.csv")
@admin_required
def admin_export_feedback():
    """Stream all feedback as a CSV download. UTF-8 with BOM so Excel renders cleanly."""
    import csv
    import io
    from flask import Response

    rows = db.list_feedback(limit=10000) if db.is_enabled() else []

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow([
        "ID", "Timestamp", "Rating", "User Question", "Bot Reply",
        "Comment", "Persona"
    ])
    for r in rows:
        writer.writerow([
            r.get("id", ""),
            r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("created_at") else "",
            r.get("rating", ""),
            r.get("user_message", "") or "",
            r.get("bot_reply", "") or "",
            r.get("comment", "") or "",
            r.get("persona", "") or "",
        ])

    # Prepend UTF-8 BOM so Excel decodes em-dashes, smart quotes, accented characters correctly
    csv_content = "\ufeff" + output.getvalue()
    output.close()

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"j3p_feedback_{timestamp}.csv"

    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@app.route("/admin/export/feedback.xlsx")
@admin_required
def admin_export_feedback_xlsx():
    """Stream all feedback as an Excel (.xlsx) download with formatting."""
    from flask import Response
    from datetime import datetime
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return ("Excel export unavailable: openpyxl not installed. "
                "Use CSV export instead, or add 'openpyxl' to requirements.txt."), 500

    rows = db.list_feedback(limit=10000) if db.is_enabled() else []

    wb = Workbook()
    ws = wb.active
    ws.title = "Feedback"

    headers = ["ID", "Timestamp", "Rating", "User Question", "Bot Reply", "Comment", "Persona"]
    ws.append(headers)

    # Header styling — navy background, gold text, bold
    header_font = Font(bold=True, color="D2BC8D", size=11)
    header_fill = PatternFill("solid", fgColor="27334A")
    header_align = Alignment(horizontal="left", vertical="center", wrap_text=False)
    thin_border = Border(
        bottom=Side(style="medium", color="27334A"),
    )
    for col_idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # Data rows
    wrap_align = Alignment(vertical="top", wrap_text=True)
    down_fill = PatternFill("solid", fgColor="FEEAE5")  # subtle rust tint for thumbs-down rows
    for r in rows:
        ws.append([
            r.get("id", ""),
            r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("created_at") else "",
            r.get("rating", ""),
            r.get("user_message", "") or "",
            r.get("bot_reply", "") or "",
            r.get("comment", "") or "",
            r.get("persona", "") or "",
        ])
        row_idx = ws.max_row
        # Highlight thumbs-down rows so they're easy to spot when reviewing
        if r.get("rating") == "down":
            for col_idx in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col_idx).fill = down_fill
        # Wrap long text cells
        for col_idx in [4, 5, 6]:  # User Question, Bot Reply, Comment
            ws.cell(row=row_idx, column=col_idx).alignment = wrap_align

    # Column widths — sized for readable browsing in Excel
    column_widths = {
        "A": 8,    # ID
        "B": 20,   # Timestamp
        "C": 8,    # Rating
        "D": 50,   # User Question
        "E": 80,   # Bot Reply
        "F": 40,   # Comment
        "G": 18,   # Persona
    }
    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    # Freeze the header row so it stays visible while scrolling
    ws.freeze_panes = "A2"

    # AutoFilter on the header so user can sort/filter in Excel
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"

    # Stream to a BytesIO
    import io
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"j3p_feedback_{timestamp}.xlsx"

    return Response(
        buffer.read(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@app.route("/admin/feedback/delete-selected", methods=["POST"])
@admin_required
def admin_delete_selected_feedback():
    """Delete one or more feedback rows by ID (checkboxes from the table)."""
    ids = request.form.getlist("feedback_ids")
    if not ids:
        flash("No feedback rows selected.")
        return redirect(url_for("admin_dashboard"))
    try:
        count = db.delete_feedback_ids(ids)
        flash(f"Deleted {count} feedback row{'s' if count != 1 else ''}.")
    except Exception as e:
        app.logger.error(f"Delete selected feedback failed: {e}")
        flash(f"Delete failed: {str(e)[:200]}")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/feedback/delete-all", methods=["POST"])
@admin_required
def admin_delete_all_feedback():
    """Wipe ALL feedback. Form must include confirm='YES' to prevent accidents."""
    confirm = (request.form.get("confirm") or "").strip()
    if confirm != "YES":
        flash("Clear-all cancelled — confirmation text did not match.")
        return redirect(url_for("admin_dashboard"))
    try:
        count = db.delete_all_feedback()
        flash(f"Cleared all feedback ({count} rows).")
    except Exception as e:
        app.logger.error(f"Delete all feedback failed: {e}")
        flash(f"Clear failed: {str(e)[:200]}")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/feedback/<int:feedback_id>/approve-lesson", methods=["POST"])
@admin_required
def admin_approve_lesson(feedback_id):
    """Approve a thumbs-down feedback row as a learning example.

    Embeds the user's original question and stores it on the feedback row.
    From this point forward, the bot will see this lesson when answering
    semantically similar questions.
    """
    if not (db.is_enabled() and emb.is_enabled()):
        flash("Cannot approve lesson — database or embeddings not configured.")
        return redirect(url_for("admin_dashboard"))

    row = db.get_feedback(feedback_id)
    if not row:
        flash("Feedback row not found.")
        return redirect(url_for("admin_dashboard"))
    if row.get("rating") != "down":
        flash("Only thumbs-down feedback can be approved as a lesson.")
        return redirect(url_for("admin_dashboard"))
    if not (row.get("comment") or "").strip():
        flash("This feedback has no comment — nothing to learn from. Add a comment first.")
        return redirect(url_for("admin_dashboard"))

    try:
        question_embedding = emb.embed_text(row["user_message"] or "")
        ok = db.approve_feedback_as_lesson(feedback_id, question_embedding)
        if ok:
            flash(f"✓ Lesson approved — the bot will now learn from feedback #{feedback_id}.")
        else:
            flash(f"Could not approve feedback #{feedback_id} (not eligible).")
    except Exception as e:
        app.logger.error(f"Approve lesson failed: {e}")
        flash(f"Approve failed: {str(e)[:200]}")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/feedback/<int:feedback_id>/revoke-lesson", methods=["POST"])
@admin_required
def admin_revoke_lesson(feedback_id):
    """Stop using this feedback as a lesson going forward."""
    try:
        ok = db.revoke_feedback_lesson(feedback_id)
        if ok:
            flash(f"Lesson revoked — feedback #{feedback_id} no longer informs the bot.")
        else:
            flash(f"Feedback #{feedback_id} not found.")
    except Exception as e:
        flash(f"Revoke failed: {str(e)[:200]}")
    return redirect(url_for("admin_dashboard"))


@app.route("/webhook/email", methods=["POST"])
def email_webhook():
    """
    Postmark inbound email webhook.

    Configure in Postmark: Servers → Inbound → Server settings → set webhook URL to
    https://web-production-901d85.up.railway.app/webhook/email

    Security model:
      - Subject line MUST contain the secret keyword from EMAIL_INGEST_KEYWORD env var
        (case-insensitive substring match). Without that, the email is rejected.
      - This protects against anyone who guesses the inbound email address.

    What gets ingested:
      - Email body (text version) becomes one document
      - Each PDF / DOCX / TXT / MD attachment becomes its own separate document
      - Each document is titled with the email subject + filename for attachments

    Postmark returns 200 to ANY response. We always return 200 even on rejected emails
    so Postmark doesn't retry — but we log the rejection reason.
    """
    if not (db.is_enabled() and emb.is_enabled()):
        app.logger.error("Email webhook hit but DB or embeddings not configured")
        return jsonify({"status": "rejected", "reason": "service-not-configured"}), 200

    keyword = (os.environ.get("EMAIL_INGEST_KEYWORD") or "").strip().lower()
    if not keyword:
        app.logger.error("Email webhook hit but EMAIL_INGEST_KEYWORD not set — rejecting all")
        return jsonify({"status": "rejected", "reason": "keyword-not-configured"}), 200

    payload = request.get_json(silent=True) or {}
    subject = (payload.get("Subject") or "").strip()
    from_email = (payload.get("FromFull") or {}).get("Email") or payload.get("From") or "unknown"

    # Security gate: subject MUST contain the secret keyword
    if keyword not in subject.lower():
        app.logger.warning(
            f"Email webhook rejected — subject missing keyword. From: {from_email}, Subject: {subject!r}"
        )
        return jsonify({"status": "rejected", "reason": "missing-keyword"}), 200

    # Strip the keyword from subject so the doc title is cleaner.
    # Removes "[KEYWORD]" or "KEYWORD:" or just "KEYWORD" patterns.
    import re
    clean_subject = re.sub(
        rf"\[?\b{re.escape(keyword)}\b\]?[\s:]*",
        "",
        subject,
        flags=re.IGNORECASE,
    ).strip()
    if not clean_subject:
        clean_subject = "Email submission"

    text_body = (payload.get("TextBody") or "").strip()
    html_body = (payload.get("HtmlBody") or "").strip()
    attachments = payload.get("Attachments") or []

    ingested = []
    errors = []

    # ---- Ingest the email body (if it has substance) ----
    if text_body and len(text_body) > 50:
        try:
            body_dup = db.find_duplicate_document(title=clean_subject)
            if body_dup:
                errors.append({
                    "kind": "body",
                    "error": f"duplicate-of-doc-{body_dup['id']}",
                    "skipped_title": clean_subject,
                })
                app.logger.info(
                    f"Email body skipped — duplicate of doc #{body_dup['id']} ({clean_subject!r})"
                )
            else:
                chunks = emb.chunk_text(text_body)
                if chunks:
                    vectors = emb.embed_batch(chunks)
                    pairs = list(zip(chunks, vectors))
                    doc_id = db.insert_document(
                        clean_subject,
                        f"email:{from_email}",
                        pairs,
                    )
                    ingested.append({
                        "kind": "body",
                        "title": clean_subject,
                        "doc_id": doc_id,
                        "chunks": len(chunks),
                    })
                    app.logger.info(f"Email body ingested: doc #{doc_id}, {len(chunks)} chunks")
        except Exception as e:
            app.logger.error(f"Email body ingest failed: {e}")
            errors.append({"kind": "body", "error": str(e)[:200]})

    # ---- Ingest each attachment ----
    import base64
    SUPPORTED_EXT = (".pdf", ".docx", ".txt", ".md")
    for att in attachments:
        att_name = att.get("Name") or "attachment"
        content_b64 = att.get("Content") or ""
        if not content_b64:
            continue
        if not att_name.lower().endswith(SUPPORTED_EXT):
            errors.append({
                "kind": "attachment",
                "name": att_name,
                "error": "unsupported-extension",
            })
            continue
        # Title uses subject + filename so multiple attachments are distinguishable
        doc_title = f"{clean_subject} — {att_name}" if clean_subject else att_name
        # Duplicate check before embedding work
        att_dup = db.find_duplicate_document(title=doc_title)
        if att_dup:
            errors.append({
                "kind": "attachment",
                "name": att_name,
                "error": f"duplicate-of-doc-{att_dup['id']}",
            })
            app.logger.info(
                f"Email attachment skipped — duplicate of doc #{att_dup['id']} ({doc_title!r})"
            )
            continue
        try:
            file_bytes = base64.b64decode(content_b64)
            text = emb.extract_text_from_upload(att_name, file_bytes)
            if not text.strip():
                errors.append({"kind": "attachment", "name": att_name, "error": "no-text-extracted"})
                continue
            chunks = emb.chunk_text(text)
            if not chunks:
                errors.append({"kind": "attachment", "name": att_name, "error": "no-chunks"})
                continue
            vectors = emb.embed_batch(chunks)
            pairs = list(zip(chunks, vectors))
            doc_id = db.insert_document(doc_title, f"email:{from_email}:{att_name}", pairs)
            ingested.append({
                "kind": "attachment",
                "title": doc_title,
                "doc_id": doc_id,
                "chunks": len(chunks),
            })
            app.logger.info(f"Email attachment ingested: {att_name} -> doc #{doc_id}, {len(chunks)} chunks")
        except Exception as e:
            app.logger.error(f"Email attachment ingest failed for {att_name}: {e}")
            errors.append({"kind": "attachment", "name": att_name, "error": str(e)[:200]})

    app.logger.info(
        f"Email webhook complete. From: {from_email}, Subject: {clean_subject}, "
        f"Ingested: {len(ingested)}, Errors: {len(errors)}"
    )
    return jsonify({
        "status": "ok",
        "from": from_email,
        "subject": clean_subject,
        "ingested": ingested,
        "errors": errors,
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
