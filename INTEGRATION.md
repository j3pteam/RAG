# Personality assessment → advisor persona: integration

Drops into j3pteam/RAG. Fills the **Personality assessment** slot in the advisor's onboarding (Big Five + under-pressure derailers, one step, 37 items) and feeds the results into that advisor's system prompt. The existing **Self behavioral assessment** and **360 feedback** are untouched.

## 1. Copy
Put `assessment/` at the repo root, next to the Flask app.

## 2. Storage
```sql
CREATE TABLE advisor_personality (
  advisor_id   TEXT PRIMARY KEY,
  answers      JSON NOT NULL,
  scores       JSON NOT NULL,
  completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 3. Register the blueprint
```python
from assessment import create_assessment_blueprint

app.register_blueprint(create_assessment_blueprint(
    get_advisor=lambda token: ...,               # portal token -> {"id","name"} or None
    get_advisor_by_id=lambda advisor_id: ...,    # -> {"id","name"} or None
    get_result=lambda advisor_id: ...,           # row as dict or None
    save_result=lambda advisor_id, answers, scores: ...,   # upsert, set completed_at
    onboarding_home=lambda token: ...,           # URL of the advisor's onboarding page
    admin_required=admin_required,               # existing admin decorator
))
```
Routes added:
- `/portal/<token>/onboarding/personality` — advisor takes or reviews it; saving returns to onboarding
- `/admin/advisors/<id>/personality` — admin results view

## 4. Show it in onboarding

**Admin → J3P Advisors → Onboarding (Personality assessment column).** Replace that column's "Not yet completed" text with:
```jinja
{% with result=personality_result, advisor=advisor, portal_token=advisor.portal_token %}
  {% include "_admin_personality_tile.html" %}
{% endwith %}
```
The admin view passes `personality_result = get_result(advisor.id)`. Use whatever field holds the advisor's portal-link token in place of `advisor.portal_token`. The column then shows:
- the status, "Not yet completed" or "Completed <date>"
- **View results**, once completed
- **Open assessment**, which opens the advisor's assessment in a new tab
- **Copy link for advisor**, a direct link you can send them

**Advisor's own onboarding page:**
```jinja
{% with result=personality_result, token=token %}{% include "_onboarding_tile.html" %}{% endwith %}
```

## 5. Completion gate
Wherever the portal currently checks that the personality assessment is done before unlocking, point that check at `get_result(advisor_id)`. Leave the behavioral check as it is.

## 6. Inject into the persona
Where the advisor's system prompt is built, next to Areas of Expertise:
```python
from assessment import build_persona_block

r = get_result(advisor.id)
system_prompt += "\n\n" + build_persona_block(advisor.name, r["scores"] if r else None)
```
Returns an empty string until the assessment exists.

## How results become persona
- **High/low traits** set tone and structure. Moderate traits add nothing.
- **Elevated derailers are not imitated.** Each adds a counterweight, so the bot keeps the advisor's strengths without their stress behaviors.
- **No scores or labels go in the prompt**, so results can't leak to participants.

Wording lives in `persona.py`; cut-offs in `items.py` (`trait_band`, `derailer_band`).

## Notes
- Original items, not Hogan content; not validated. Developmental use only.
- Retakes overwrite the row. To keep history, key on `(advisor_id, completed_at)`.
