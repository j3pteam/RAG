"""Flask blueprint for the advisor-portal assessments.

Storage is injected so this works with whatever DB layer the app already uses:
  get_advisor(token)                     -> {"id", "name"} or None
  get_result(advisor_id, instrument)     -> stored dict or None
  save_result(advisor_id, instrument, answers, scores) -> None
  portal_home(token)                     -> URL to return to when done
"""
import os
from flask import Blueprint, abort, redirect, render_template, request

from .items import INSTRUMENTS, LIKERT, score

ORDER = ["personality", "behavioral"]


def create_assessment_blueprint(get_advisor, get_result, save_result, portal_home):
    bp = Blueprint("assessment", __name__,
                   template_folder=os.path.join(os.path.dirname(__file__), "templates"))

    @bp.route("/portal/<token>/assessment/<instrument>", methods=["GET", "POST"])
    def take(token, instrument):
        advisor = get_advisor(token)
        if not advisor or instrument not in INSTRUMENTS:
            abort(404)
        inst = INSTRUMENTS[instrument]
        error, answers = None, {}

        if request.method == "POST":
            answers = {k: request.form[k] for k, _ in inst["items"] if request.form.get(k)}
            try:
                scores = score(instrument, answers)
            except ValueError as e:
                error = f"Please answer every statement ({e})."
            else:
                save_result(advisor["id"], instrument, {k: int(v) for k, v in answers.items()}, scores)
                nxt = next((i for i in ORDER[ORDER.index(instrument) + 1:]
                            if not get_result(advisor["id"], i)), None)
                return redirect(f"/portal/{token}/assessment/{nxt}" if nxt else portal_home(token))
        elif get_result(advisor["id"], instrument):
            answers = get_result(advisor["id"], instrument).get("answers", {})

        return render_template("assessment_form.html", advisor=advisor, inst=inst,
                               instrument=instrument, likert=LIKERT, answers=answers,
                               error=error, step=ORDER.index(instrument) + 1, steps=len(ORDER))

    return bp
