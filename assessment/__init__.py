"""Personality assessment (onboarding step) -> persona block for the J3P Advisor."""
from .routes import create_assessment_blueprint
from .persona import build_persona_block
from .items import PARTS, score
from .reports import build_coach_report, build_self_report
