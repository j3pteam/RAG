#!/usr/bin/env python3
"""
Adds per-advisor Participant Links back into the admin panel.

Run from the directory containing app.py:

    python3 patch_participant_links.py

What it changes
---------------
1. public_base_url() helper — all admin-panel links render as https://
   instead of http:// (Railway terminates TLS, so request.host_url is http).
2. A "Participant Links" section inside every advisor card, and inside the
   default-persona block: create a link, and an inline list with
   Copy / Share / Enable / Disable / Delete.
3. return_to plumbing so those forms redirect back to the Advisors tab
   instead of jumping to the Participant links tab.
4. The tab bar now honours the URL hash, so those redirects actually land.

Safety
------
Every edit asserts an exact match count. Nothing is written unless all of
them pass, the result parses as Python, and ADMIN_HTML compiles as Jinja.
The original is backed up to app.py.bak first.
"""
import ast
import shutil
import sys

PATH = "app.py"

with open(PATH, encoding="utf-8") as fh:
    s = fh.read()

original_len = len(s)
steps = []


def sub(label, old, new, count=1):
    """Replace `old` exactly `count` times, or abort."""
    global s
    found = s.count(old)
    if found != count:
        print(f"ABORT [{label}]: expected {count} match(es), found {found}")
        print("  anchor was:")
        for line in old.splitlines()[:4]:
            print("    " + line)
        sys.exit(1)
    s = s.replace(old, new)
    steps.append(f"{label} ({count})")


# ---------------------------------------------------------------------------
# 1. public_base_url() + the redirect helper
# ---------------------------------------------------------------------------

sub(
    "helpers: public_base_url + _participant_link_redirect",
    'ADMIN_LOGIN_HTML = """<!DOCTYPE html>',
    '''def public_base_url() -> str:
    """The app's own public origin, always https.

    Railway terminates TLS at the edge and forwards plain HTTP, so
    request.host_url comes back as http:// — which is what every link in
    the admin panel was showing. PUBLIC_BASE_URL wins when it is set;
    otherwise the scheme is corrected here rather than at each call site.
    """
    base = (paywall.PUBLIC_BASE_URL or request.host_url or "").rstrip("/")
    if base.startswith("http://"):
        base = "https://" + base[len("http://"):]
    return base


def _participant_link_redirect():
    """Where to land after a participant-link change.

    A link created from inside an advisor card should return to that card,
    not throw the admin over to the Participant links tab — so these forms
    post a return_to field and this honours it. Anything else keeps the
    original behaviour.
    """
    if (request.form.get("return_to") or "").strip() == "advisors":
        return redirect(url_for("admin_dashboard") + "#advisors")
    return redirect(url_for("admin_dashboard") + "#participant-links")


ADMIN_LOGIN_HTML = """<!DOCTYPE html>''',
)

# ---------------------------------------------------------------------------
# 2. Route every participant-link redirect through the helper
# ---------------------------------------------------------------------------

sub(
    "participant-link redirects",
    'return redirect(url_for("admin_dashboard") + "#participant-links")',
    "return _participant_link_redirect()",
    count=7,
)

# ---------------------------------------------------------------------------
# 3. https base URL at all three call sites
# ---------------------------------------------------------------------------

sub(
    "base_url: admin dashboard",
    'base_url=(paywall.PUBLIC_BASE_URL or request.host_url.rstrip("/")),',
    "base_url=public_base_url(),",
)

sub(
    "base_url: bulk create export",
    '''    base_url = (paywall.PUBLIC_BASE_URL or request.host_url.rstrip("/"))
    advisor_names = {a["slug"]: a["name"] for a in list_advisors()}''',
    '''    base_url = public_base_url()
    advisor_names = {a["slug"]: a["name"] for a in list_advisors()}''',
)

sub(
    "base_url: export rows",
    '''    base_url = (paywall.PUBLIC_BASE_URL or request.host_url.rstrip("/"))
    out = []''',
    """    base_url = public_base_url()
    out = []""",
)

# ---------------------------------------------------------------------------
# 4. Group participant links by advisor for the dashboard
# ---------------------------------------------------------------------------

sub(
    "dashboard: group links by advisor",
    """    _advisor_docs = {}
    for d in docs:
        for slug in _advisor_map.get(d["title"], []):
            _advisor_docs.setdefault(slug, []).append(d)
    return _cached_render(""",
    '''    _advisor_docs = {}
    for d in docs:
        for slug in _advisor_map.get(d["title"], []):
            _advisor_docs.setdefault(slug, []).append(d)
    # One pass, reused by both the Participant links tab and the per-advisor
    # sections inside each advisor card. "" is the default persona.
    _participant_links = list_participant_links()
    _links_by_advisor = {}
    for _l in _participant_links:
        _links_by_advisor.setdefault(_l["advisor_slug"] or "", []).append(_l)
    return _cached_render(''',
)

sub(
    "dashboard: pass grouped links to the template",
    "        participant_links=list_participant_links(),",
    """        participant_links=_participant_links,
        participant_links_by_advisor=_links_by_advisor,""",
)

# ---------------------------------------------------------------------------
# 5. The macro itself
# ---------------------------------------------------------------------------

MACRO = r'''    {% endmacro %}

    {% macro participant_links_section(t_slug, t_name, t_links, can_edit) %}
      <details class="advisor-section">
        <summary>Participant Links{% if t_links %} ({{ t_links|length }}){% endif %}</summary>
        <p class="muted" style="margin: 0 0 0.7rem; font-size: 0.78rem;">
          Dedicated links for specific people, landing on {{ t_name }}. Each one
          keeps that person's conversation across visits and devices, and can be
          switched off at any time without deleting their history.
        </p>
        {% if can_edit %}
        <form method="POST" action="{{ url_for('admin_create_participant_link') }}"
              style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;
                     margin-bottom: 0.9rem;">
          <input type="hidden" name="advisor_slug" value="{{ t_slug }}" />
          <input type="hidden" name="return_to" value="advisors" />
          <input type="text" name="label" required
                 placeholder="Label for your own reference (e.g. Jane Smith)"
                 style="flex: 2 1 220px; padding: 0.45rem; border: 1px solid var(--line);
                        border-radius: 2px; font-family: inherit; font-size: 0.82rem;" />
          <input type="text" name="first_name" placeholder="First name (greeting)"
                 style="flex: 1 1 140px; padding: 0.45rem; border: 1px solid var(--line);
                        border-radius: 2px; font-family: inherit; font-size: 0.82rem;" />
          <input type="email" name="email" placeholder="Email (optional)"
                 style="flex: 1 1 160px; padding: 0.45rem; border: 1px solid var(--line);
                        border-radius: 2px; font-family: inherit; font-size: 0.82rem;" />
          <button type="submit" class="btn" style="font-size: 0.64rem;">Create link</button>
        </form>
        {% endif %}
        {% if t_links %}
        <table style="font-size: 0.8rem;">
          <tr>
            <th style="width: 20%;">Label</th><th>Link</th>
            <th style="width: 10%;">Status</th><th style="width: 12%;">Last used</th>
            {% if can_edit %}<th style="width: 14%;"></th>{% endif %}
          </tr>
          {% for l in t_links %}
          <tr>
            <td>
              {{ l.label }}
              {% if l.first_name %}<br /><span class="muted" style="font-size: 0.72rem;">{{ l.first_name }}</span>{% endif %}
            </td>
            <td>
              <div style="display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap;">
                <a href="{{ base_url }}/p/{{ l.token }}" target="_blank"
                   class="adv-link">{{ base_url }}/p/{{ l.token }}</a>
                <button type="button" class="copy-link"
                        data-url="{{ base_url }}/p/{{ l.token }}">Copy</button>
                <button type="button" class="share-link"
                        data-url="{{ base_url }}/p/{{ l.token }}"
                        data-advisor="{{ t_name }}">Share</button>
              </div>
            </td>
            <td>
              {% if l.enabled %}<span style="color: #2D7D5F;">Enabled</span>
              {% else %}<span class="muted">Disabled</span>{% endif %}
            </td>
            <td class="muted">{{ l.last_used_at.strftime("%Y-%m-%d") if l.last_used_at else "Never" }}</td>
            {% if can_edit %}
            <td>
              <div style="display: flex; gap: 0.35rem; flex-wrap: wrap;">
                <form method="POST" action="{{ url_for('admin_toggle_participant_link', link_id=l.id) }}">
                  <input type="hidden" name="enable" value="{{ '0' if l.enabled else '1' }}" />
                  <input type="hidden" name="return_to" value="advisors" />
                  <button type="submit" class="btn" style="font-size: 0.6rem;">
                    {{ "Disable" if l.enabled else "Enable" }}
                  </button>
                </form>
                <form method="POST" action="{{ url_for('admin_delete_participant_link', link_id=l.id) }}"
                      onsubmit="return confirm('Delete this participant link? It cannot be undone.');">
                  <input type="hidden" name="return_to" value="advisors" />
                  <button type="submit" class="btn-danger" style="font-size: 0.6rem;">Delete</button>
                </form>
              </div>
            </td>
            {% endif %}
          </tr>
          {% endfor %}
        </table>
        {% else %}
        <p class="muted" style="margin: 0; font-size: 0.8rem;">
          No participant links for {{ t_name }} yet.
        </p>
        {% endif %}
      </details>
    {% endmacro %}

  <div class="tab-pane" data-tab="advisors">'''

sub(
    "macro: participant_links_section",
    '''    {% endmacro %}

  <div class="tab-pane" data-tab="advisors">''',
    MACRO,
)

# ---------------------------------------------------------------------------
# 6. Call it — default persona, then each named advisor
# ---------------------------------------------------------------------------

sub(
    "call: default persona",
    """      {{ voice_sample_section(default_persona_slug, settings.avatar_name or cfg.persona_name,
                               default_persona_voice_sample, admin_perms.edit_voice) }}
    </div>""",
    """      {{ voice_sample_section(default_persona_slug, settings.avatar_name or cfg.persona_name,
                               default_persona_voice_sample, admin_perms.edit_voice) }}

      {{ participant_links_section("", settings.avatar_name or cfg.persona_name,
                                   participant_links_by_advisor.get("", []),
                                   admin_perms.edit_participant_links) }}
    </div>""",
)

sub(
    "call: named advisors",
    """      {{ voice_sample_section(adv.slug, adv.name, adv.voice_sample, admin_perms.edit_voice) }}

      <details class="advisor-section">
        <summary>Scheduling Links</summary>""",
    """      {{ voice_sample_section(adv.slug, adv.name, adv.voice_sample, admin_perms.edit_voice) }}

      {{ participant_links_section(adv.slug, adv.name,
                                   participant_links_by_advisor.get(adv.slug, []),
                                   admin_perms.edit_participant_links) }}

      <details class="advisor-section">
        <summary>Scheduling Links</summary>""",
)

# ---------------------------------------------------------------------------
# 7. Tabs honour the URL hash, so #advisors actually lands on Advisors
# ---------------------------------------------------------------------------

sub(
    "tabs: activate from URL hash",
    """        let saved = null;
        try { saved = localStorage.getItem(KEY); } catch (e) {}
        if (saved && tabs.some(t => t.dataset.tab === saved)) activate(saved);""",
    """        // A redirect carrying #advisors (or any other tab name) wins over
        // whatever tab was last open — otherwise a form posted from inside an
        // advisor card lands back on a different tab entirely.
        const fromHash = (location.hash || "").replace("#", "");
        if (fromHash && tabs.some(t => t.dataset.tab === fromHash)) {
          activate(fromHash);
          try { localStorage.setItem(KEY, fromHash); } catch (e) {}
        } else {
          let saved = null;
          try { saved = localStorage.getItem(KEY); } catch (e) {}
          if (saved && tabs.some(t => t.dataset.tab === saved)) activate(saved);
        }""",
)

# ---------------------------------------------------------------------------
# Validate before writing anything
# ---------------------------------------------------------------------------

try:
    tree = ast.parse(s)
except SyntaxError as e:
    print(f"ABORT: result is not valid Python — {e}")
    sys.exit(1)

# Pull ADMIN_HTML straight out of the patched source and compile it as Jinja,
# so a template typo fails here rather than at the next admin page load.
admin_html = None
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == "ADMIN_HTML" for t in node.targets
    ):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            admin_html = node.value.value

if admin_html is None:
    print("ABORT: could not find ADMIN_HTML in the patched file")
    sys.exit(1)

try:
    import jinja2

    jinja2.Environment().from_string(admin_html)
except ImportError:
    print("NOTE: jinja2 not importable here — skipped the template compile check")
except Exception as e:
    print(f"ABORT: ADMIN_HTML no longer compiles as Jinja — {e}")
    sys.exit(1)

for needed in ("participant_links_section", "participant_links_by_advisor"):
    if admin_html.count(needed) < 2:
        print(f"ABORT: {needed} did not land in the template as expected")
        sys.exit(1)

shutil.copy(PATH, PATH + ".bak")
with open(PATH, "w", encoding="utf-8") as fh:
    fh.write(s)

print("Patched app.py (original saved as app.py.bak)")
print(f"  {original_len} -> {len(s)} bytes")
for step in steps:
    print("  - " + step)
print()
print("Bump APP_VERSION before deploying so you can tell the builds apart.")
