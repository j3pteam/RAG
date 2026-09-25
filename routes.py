"""Flask blueprint for the Personality assessment step of advisor onboarding.

Storage and auth are injected so this fits the app's existing layers:
  get_advisor(token)                -> {"id", "name"} or None   (portal-link token)
  get_advisor_by_id(advisor_id)     -> {"id", "name"} or None   (admin view)
  get_result(advisor_id)            -> {"answers","scores","completed_at"} or None
  save_result(advisor_id, answers, scores) -> None               (upsert)
  onboarding_home(token)            -> URL of the advisor's onboarding page
  admin_required                    -> the app's existing admin-auth decorator
"""
import os
from flask import Blueprint, abort, redirect, render_template, request

from .items import ALL_ITEM_IDS, DERAILERS, LIKERT, PARTS, TRAITS, score


def create_assessment_blueprint(get_advisor, get_advisor_by_id, get_result, save_result,
                                onboarding_home, admin_required):
    bp = Blueprint("personality_assessment", __name__,
                   template_folder=os.path.join(os.path.dirname(__file__), "templates"))

    @bp.route("/portal/<token>/onboarding/personality", methods=["GET", "POST"])
    def take(token):
        advisor = get_advisor(token)
        if not advisor:
            abort(404)
        error, answers = None, {}
        if request.method == "POST":
            answers = {k: request.form[k] for k in ALL_ITEM_IDS if request.form.get(k)}
            try:
                scores = score(answers)
            except ValueError as e:
                error = f"Please answer every statement ({e})."
            else:
                save_result(advisor["id"], {k: int(v) for k, v in answers.items()}, scores)
                return redirect(onboarding_home(token))
        else:
            prior = get_result(advisor["id"])
            answers = prior["answers"] if prior else {}
        return render_template("personality_assessment.html", advisor=advisor, parts=PARTS,
                               likert=LIKERT, answers=answers, error=error,
                               back_url=onboarding_home(token))

    @bp.route("/admin/advisors/<advisor_id>/personality")
    @admin_required
    def admin_view(advisor_id):
        advisor, result = get_advisor_by_id(advisor_id), get_result(advisor_id)
        if not advisor:
            abort(404)
        return render_template("personality_results.html", advisor=advisor, result=result,
                               trait_names={k: v[0] for k, v in TRAITS.items()},
                               derailer_names={k: v[0] for k, v in DERAILERS.items()})

    return bp
