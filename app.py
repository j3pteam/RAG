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
        "https://j3phealth.as.me/schedule/81cec0b7",
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
      display: flex; gap: 0.4rem; margin-top: 0.6rem;
      padding-top: 0.6rem; border-top: 1px solid var(--line); align-items: center;
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

    /* Action buttons (copy + share) — mirror feedback-btn style */
    .action-sep {
      width: 1px; height: 22px; background: var(--line);
      margin: 0 0.2rem;
    }
    .action-btn {
      background: transparent; border: 1px solid var(--line);
      color: var(--muted); width: 30px; height: 30px; border-radius: 50%;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      padding: 0; transition: all 0.18s ease;
      position: relative;
    }
    .action-btn svg { width: 14px; height: 14px; }
    .action-btn:hover { border-color: var(--gold); color: var(--navy); background: var(--paper); }
    .action-btn.copied { background: var(--navy); border-color: var(--navy); color: var(--gold); }
    .action-toast {
      position: absolute; bottom: calc(100% + 6px); left: 50%; transform: translateX(-50%);
      background: var(--navy); color: var(--gold);
      font-size: 0.65rem; letter-spacing: 0.1em; text-transform: uppercase;
      padding: 0.3rem 0.6rem; border-radius: 2px; white-space: nowrap;
      opacity: 0; pointer-events: none; transition: opacity 0.18s ease;
    }
    .action-toast.show { opacity: 1; }

    /* Share menu popover */
    .share-wrap { position: relative; }
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
    }
    .share-menu a:hover, .share-menu button:hover { background: var(--paper); color: var(--navy); }
    .share-menu svg { width: 16px; height: 16px; flex-shrink: 0; color: var(--muted); }
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
    input[type="text"] {
      flex: 1; padding: 0.85rem 3.2rem 0.85rem 1.1rem;
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
      input[type="text"] { padding: 0.75rem 2.9rem 0.75rem 0.9rem; font-size: 16px; }
      button[type="submit"] { padding: 0.75rem 1rem; font-size: 0.7rem; letter-spacing: 0.12em; }
      .footer-note { font-size: 0.62rem; letter-spacing: 0.1em; }
    }
    /* Very narrow phones: hide the persona tag + divider, swap button to icon only */
    @media (max-width: 480px) {
      .brand-divider, .brand-tag { display: none; }
      .reset-label { display: none; }
      .reset-icon { display: inline-block; }
      header button { padding: 0.5rem; min-width: 38px; min-height: 38px;
                      display: inline-flex; align-items: center; justify-content: center; }
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
    <form id="chat-form">
      <div class="input-wrap">
        <input type="text" id="message" placeholder="{{ cfg.placeholder }}" autocomplete="off" autofocus required />
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

    function addMessage(text, role, withFeedback = false) {
      const div = document.createElement("div");
      div.className = "msg " + role;
      const textNode = document.createElement("div");
      textNode.textContent = text;
      div.appendChild(textNode);
      if (withFeedback) attachFeedback(div, text);
      chat.appendChild(div);
      chatWrap.scrollTop = chatWrap.scrollHeight;
      return div;
    }

    function attachFeedback(msgDiv, replyText) {
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
        <span class="action-sep"></span>
        <button class="action-btn copy-btn" aria-label="Copy answer" title="Copy answer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
          <span class="action-toast">Copied</span>
        </button>
        <span class="share-wrap">
          <button class="action-btn share-btn" aria-label="Share answer" title="Share answer">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
            </svg>
          </button>
          <div class="share-menu" role="menu"></div>
        </span>
      `;

      async function sendFeedback(rating, comment) {
        try {
          await fetch("/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ rating, reply: replyText, comment: comment || "" }),
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
      // === COPY button ===
      const copyBtn = wrap.querySelector(".copy-btn");
      const copyToast = copyBtn.querySelector(".action-toast");
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
          copyToast.classList.add("show");
          copyToast.textContent = "Copied";
          setTimeout(() => {
            copyBtn.classList.remove("copied");
            copyToast.classList.remove("show");
          }, 1600);
        } catch (err) {
          console.error("Copy failed:", err);
          copyToast.textContent = "Failed";
          copyToast.classList.add("show");
          setTimeout(() => copyToast.classList.remove("show"), 1600);
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

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      addMessage(text, "user");
      input.value = "";
      sendBtn.disabled = true;
      const thinking = addMessage("Thinking…", "assistant typing");
      try {
        const res = await fetch("/chat", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });
        const data = await res.json();
        thinking.remove();
        if (data.reply) addMessage(data.reply, "assistant", true);
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
def index():
    session["messages"] = []
    return render_template_string(INDEX_HTML, cfg=CONFIG)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_input = (data.get("message") or "").strip()
    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    messages = session.get("messages", [])
    messages.append({"role": "user", "content": user_input})

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
        )
    else:
        composed_prompt = base_prompt + lessons_block + scope_guard

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
            messages=messages,
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

    messages.append({"role": "assistant", "content": assistant_text})
    session["messages"] = messages
    return jsonify({"reply": assistant_text})


@app.route("/reset", methods=["POST"])
def reset():
    session["messages"] = []
    return jsonify({"ok": True})


@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    reply = (data.get("reply") or "")[:20000]
    comment = (data.get("comment") or "")[:4000]
    if rating not in ("up", "down"):
        return jsonify({"error": "Invalid rating"}), 400

    messages = session.get("messages", [])
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = (m.get("content") or "")[:8000]
            break

    # Persist to DB if available, always log to stdout
    try:
        db.log_feedback(rating, last_user_msg, reply, CONFIG["persona_name"], comment)
    except Exception as e:
        app.logger.error(f"DB feedback log failed: {e}")
    app.logger.info(
        "FEEDBACK persona=%s rating=%s user_msg=%r reply=%r comment=%r",
        CONFIG["persona_name"], rating, last_user_msg, reply, comment,
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
    })


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
      <h2 style="margin: 0; border: none; padding: 0;">Recent Feedback (last 50)</h2>
      {% if stats.total > 0 %}
      <div style="display: flex; gap: 0.5rem; align-items: center;">
        <span class="muted" style="font-size: 0.78rem; margin-right: 0.3rem;">
          Export {{ stats.total }} record{{ 's' if stats.total != 1 else '' }}:
        </span>
        <a href="/admin/export/feedback.csv" class="btn" style="text-decoration: none;">
          ↓ CSV
        </a>
        <a href="/admin/export/feedback.xlsx" class="btn" style="text-decoration: none;">
          ↓ Excel
        </a>
      </div>
      {% endif %}
    </div>
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
          <th>When</th><th>Rating</th><th>User question</th><th>Bot reply</th><th>Comment</th>
          <th style="width: 60px;"></th>
        </tr>
        {% for f in feedback_rows %}
        <tr id="row-{{ f.id }}">
          <td><input type="checkbox" name="feedback_ids" value="{{ f.id }}" class="feedback-checkbox" /></td>
          <td class="muted">{{ f.created_at.strftime('%m/%d %H:%M') }}</td>
          <td>{% if f.rating == 'up' %}<span class="tag-up">UP</span>{% else %}<span class="tag-down">DOWN</span>{% endif %}{% if f.approved_for_learning %}<br /><span class="tag-lesson">LESSON</span>{% endif %}</td>
          <td class="truncate" title="{{ f.user_message }}">{{ f.user_message }}</td>
          <td class="truncate" title="{{ f.bot_reply }}">{{ f.bot_reply }}</td>
          <td class="truncate" title="{{ f.comment or '' }}" style="max-width: 280px;">
            {% if f.comment %}<strong>{{ f.comment }}</strong>{% else %}<span class="muted">—</span>{% endif %}
          </td>
          <td>
            <button type="button" class="expand-btn" data-target="detail-{{ f.id }}">
              View
            </button>
          </td>
        </tr>
        <tr id="detail-{{ f.id }}" class="feedback-detail" style="display: none;">
          <td colspan="7">
            <div class="feedback-detail-meta">
              Feedback ID #{{ f.id }} · {{ f.created_at.strftime('%A, %B %d %Y at %I:%M %p') }}
              · Rating: <strong>{% if f.rating == 'up' %}Helpful 👍{% else %}Not helpful 👎{% endif %}</strong>
              {% if f.persona %}· Persona: {{ f.persona }}{% endif %}
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
    feedback_rows = db.list_feedback(limit=50) if db_ok else []
    stats = db.feedback_stats() if db_ok else {"up": 0, "down": 0, "total": 0}
    return render_template_string(
        ADMIN_HTML, cfg=CONFIG, docs=docs, feedback_rows=feedback_rows,
        stats=stats, rag_ready=rag_ready, db_ok=db_ok, emb_ok=emb_ok,
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


@app.route("/admin/upload-url", methods=["POST"])
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
