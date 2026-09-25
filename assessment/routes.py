"""Flask blueprints for the personality assessment and its reports.

The assessment, scoring and both reports are the same for everyone who
takes it. What differs is who the person is and how they reach it, so each
kind of person gets its own blueprint from one builder:

- create_assessment_blueprint: advisors, as a step of their onboarding,
  reached through their portal-link token.
- create_participant_assessment_blueprint: participants, reached through
  their own participant-link token.

Storage and auth are injected so this fits the app's existing layers:
  get_person(token)             -> {"id", "name"} or None   (their link token)
  get_person_by_id(person_id)   -> {"id", "name"} or None   (admin views)
  get_result(person_id)         -> {"answers","scores","completed_at"} or None
  save_result(person_id, answers, scores) -> None           (upsert)
  admin_required                -> the app's existing admin-auth decorator
"""
import os
from flask import Blueprint, abort, redirect, render_template, request

from .items import ALL_ITEM_IDS, DERAILERS, LIKERT, PARTS, TRAITS, score
from .reports import build_coach_report, build_self_report

_TEMPLATES = os.path.join(os.path.dirname(__file__), "templates")

# Wording that changes with who is taking the assessment.
ADVISOR_COPY = {
    "step": "Onboarding · Personality assessment",
    "back_label": "Back to onboarding",
    "note": ("Your answers shape how your J3P advisor communicates on your behalf. "
             "Responses and scores are visible only to you and J3P administrators, "
             "and are never shown to participants."),
    "admin_back_url": "/admin?tab=advisors",
    "admin_back_label": "J3P Advisors",
}
PARTICIPANT_COPY = {
    "step": "Personality assessment",
    "back_label": "Back",
    "note": ("Your answers are used for your own development. You'll get a personal "
             "report as soon as you finish. Responses are visible only to you and "
             "the J3P team supporting you."),
    "admin_back_url": "/admin?tab=advisors",
    "admin_back_label": "Admin",
}


def _build(name, take_path, admin_path, copy, get_person, get_person_by_id,
           get_result, save_result, home_url, after_save_url, admin_required,
           person_required=None):
    """take_path and admin_path are URL prefixes containing <token> and
    <person_id>. home_url(token) is where "Back" goes; after_save_url(token)
    is where a completed assessment lands."""
    bp = Blueprint(name, __name__, template_folder=_TEMPLATES)
    guard = person_required or (lambda f: f)
    trait_names = {k: v[0] for k, v in TRAITS.items()}
    derailer_names = {k: v[0] for k, v in DERAILERS.items()}

    def admin_base(person_id):
        return admin_path.replace("<person_id>", str(person_id))

    def take_base(token):
        return take_path.replace("<token>", token)

    @bp.route(take_path, methods=["GET", "POST"])
    @guard
    def take(token):
        person = get_person(token)
        if not person:
            abort(404)
        error, answers = None, {}
        if request.method == "POST":
            answers = {k: request.form[k] for k in ALL_ITEM_IDS if request.form.get(k)}
            try:
                scores = score(answers)
            except ValueError as e:
                error = f"Please answer every statement ({e})."
            else:
                save_result(person["id"], {k: int(v) for k, v in answers.items()}, scores)
                return redirect(after_save_url(token))
        else:
            prior = get_result(person["id"])
            answers = prior["answers"] if prior else {}
        return render_template("personality_assessment.html", person=person, parts=PARTS,
                               likert=LIKERT, answers=answers, error=error, copy=copy,
                               back_url=home_url(token))

    @bp.route(take_path + "/report")
    @guard
    def self_report(token):
        person = get_person(token)
        if not person:
            abort(404)
        result = get_result(person["id"])
        if not result:
            return redirect(take_base(token))
        return render_template("personality_self_report.html",
                               report=build_self_report(person["name"], result["scores"]),
                               completed_at=result["completed_at"], back_url=home_url(token),
                               retake_url=take_base(token))

    @bp.route(admin_path + "/report")
    @admin_required
    def admin_self_report(person_id):
        """The development report exactly as the person sees it."""
        person, result = get_person_by_id(person_id), get_result(person_id)
        if not person or not result:
            abort(404)
        return render_template("personality_self_report.html",
                               report=build_self_report(person["name"], result["scores"]),
                               completed_at=result["completed_at"],
                               back_url=admin_base(person_id) + "/coach-report")

    @bp.route(admin_path + "/coach-report")
    @admin_required
    def coach_report(person_id):
        person, result = get_person_by_id(person_id), get_result(person_id)
        if not person or not result:
            abort(404)
        return render_template("personality_coach_report.html",
                               report=build_coach_report(person["name"], result["scores"]),
                               completed_at=result["completed_at"],
                               back_url=admin_base(person_id),
                               self_report_url=admin_base(person_id) + "/report")

    @bp.route(admin_path)
    @admin_required
    def admin_view(person_id):
        person, result = get_person_by_id(person_id), get_result(person_id)
        if not person:
            abort(404)
        return render_template("personality_results.html", person=person, result=result,
                               copy=copy, admin_base=admin_base(person_id),
                               trait_names=trait_names, derailer_names=derailer_names)

    return bp


def create_assessment_blueprint(get_advisor, get_advisor_by_id, get_result, save_result,
                                onboarding_home, admin_required):
    """Advisors: a step of onboarding. Adds
    /portal/<token>/onboarding/personality (+ /report) and
    /admin/advisors/<id>/personality (+ /report, /coach-report)."""
    return _build("personality_assessment",
                  "/portal/<token>/onboarding/personality",
                  "/admin/advisors/<person_id>/personality",
                  ADVISOR_COPY, get_advisor, get_advisor_by_id, get_result, save_result,
                  home_url=onboarding_home, after_save_url=onboarding_home,
                  admin_required=admin_required)


def create_participant_assessment_blueprint(get_participant, get_participant_by_id,
                                            get_result, save_result, home_url,
                                            admin_required, participant_required=None):
    """Participants: taken from their own link. Adds
    /p/<token>/personality (+ /report) and
    /admin/participants/<id>/personality (+ /report, /coach-report).
    Finishing goes straight to their development report.
    participant_required wraps the participant-facing routes (e.g. the
    same paywall as the participant's chat link)."""
    return _build("participant_assessment",
                  "/p/<token>/personality",
                  "/admin/participants/<person_id>/personality",
                  PARTICIPANT_COPY, get_participant, get_participant_by_id,
                  get_result, save_result,
                  home_url=home_url, after_save_url=lambda t: f"/p/{t}/personality/report",
                  admin_required=admin_required, person_required=participant_required)
