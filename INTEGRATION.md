# Advisor assessments → persona: integration

Drops into j3pteam/RAG. Fills the **Personality assessment** (Big Five) and **Self behavioral assessment** (derailers) slots in Admin → J3P Advisors → Onboarding, and feeds the results into that advisor's system prompt.

## 1. Copy
Put the `assessment/` folder at the repo root (next to the Flask app).

## 2. Storage
One table, any SQL DB:

```sql
CREATE TABLE advisor_assessments (
  advisor_id   TEXT NOT NULL,
  instrument   TEXT NOT NULL,          -- 'personality' | 'behavioral'
  answers      JSON NOT NULL,
  scores       JSON NOT NULL,
  completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (advisor_id, instrument)
);
```

## 3. Register the blueprint
```python
from assessment import create_assessment_blueprint

app.register_blueprint(create_assessment_blueprint(
    get_advisor=lambda token: ...,                 # advisor from portal-link token -> {"id","name"} or None
    get_result=lambda advisor_id, inst: ...,       # row as {"answers","scores","completed_at"} or None
    save_result=lambda advisor_id, inst, answers, scores: ...,  # upsert
    portal_home=lambda token: f"/portal/{token}",
))
```
Advisor URL: `/portal/<token>/assessment/personality` (continues to `behavioral` automatically).

## 4. Gate the portal
The admin copy already says both are required before the portal opens. In the portal route:
```python
for inst in ("personality", "behavioral"):
    if not get_result(advisor_id, inst):
        return redirect(f"/portal/{token}/assessment/{inst}")
```

## 5. Admin status
Replace "Not yet completed" with `completed_at` when a row exists. Optionally show the band per scale (from `scores`) to admins only.

## 6. Inject into the persona
Where the advisor's system prompt is assembled (next to Areas of Expertise):
```python
from assessment import build_persona_block

p = get_result(advisor.id, "personality")
b = get_result(advisor.id, "behavioral")
system_prompt += "\n\n" + build_persona_block(
    advisor.name,
    p["scores"] if p else None,
    b["scores"] if b else None,
)
```
Returns an empty string until assessments exist, so nothing breaks for advisors mid-onboarding.

## How results become persona
- **High/low traits** set tone and structure (e.g. low Agreeableness → candid, direct). Moderate traits add nothing.
- **Elevated derailers are not imitated.** Each adds a counterweight (e.g. elevated Arrogant → "invite the participant's view first"), so the bot carries the advisor's strengths without their stress behaviors.
- **No scores or labels go into the prompt**, so the advisor's results can't leak to participants.

Edit wording in `assessment/persona.py`; cut-offs in `items.py` (`trait_band`, `derailer_band`).

## Notes
- Items are original, not Hogan content; not a validated instrument. Developmental use only.
- Retakes overwrite the row (upsert); keep history by adding `completed_at` to the key.
- If 360 feedback is later summarized, it can be passed into `build_persona_block` the same way.
