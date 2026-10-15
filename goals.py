"""The student's editable goal: target exam, university, desired score, maximum score and exam date.

exam_name / exam_date already lived on the students row (the study planner uses them); the university, target score and marks scale are new columns
(migration 13). Validation is pure so it is unit-tested; saving goes through db.update_student, which touches only these fields.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import config
import dashboard_data
import progress
from db import get_student, update_student

EXAMS = list(config.EXAM_PRESETS)


def default_scale(exam: str) -> int:
    return int(config.EXAM_PRESETS.get(exam, config.EXAM_PRESETS["Other"]))


def get_goal(student: dict[str, Any]) -> dict[str, Any]:
    """The goal as stored. ``is_set`` is False until the student has chosen an exam; the scale falls back to the exam's preset."""
    exam = (student.get("exam_name") or "").strip()
    scale = student.get("goal_scale") or (default_scale(exam) if exam else config.SCORE_SCALE)
    score = student.get("goal_score")
    return {"is_set": bool(exam), "exam": exam, "university": (student.get("goal_university") or "").strip(), "score": int(score) if score else None,
            "scale": int(scale), "date": student.get("exam_date") or "", "days": dashboard_data.days_to_exam(student.get("exam_date"))}


def validate(exam: str, university: str, score: Any, scale: Any, exam_date: date | None, today: date | None = None) -> tuple[dict[str, Any] | None, list[str]]:
    """Returns (clean values, []) or (None, [problems]). A past exam date is rejected; a target of 0 means 'no target score'."""
    today = today or progress.local_today()
    errors: list[str] = []
    exam = (exam or "").strip()
    university = " ".join((university or "").split())
    if not exam:
        errors.append("Choose or type the exam you are preparing for.")
    if len(exam) > 40:
        errors.append("The exam name is too long (40 characters at most).")
    if len(university) > 80:
        errors.append("The university name is too long (80 characters at most).")
    try:
        scale_i = int(scale)
    except (TypeError, ValueError):
        scale_i = 0
    if not 1 <= scale_i <= config.GOAL_MAX_SCALE:
        errors.append(f"The maximum score must be a whole number from 1 to {config.GOAL_MAX_SCALE}.")
    try:
        score_i = int(score or 0)
    except (TypeError, ValueError):
        score_i = -1
    if score_i < 0 or (scale_i and score_i > scale_i):
        errors.append("The target score must be between 0 and the maximum score." if scale_i else "The target score must be a whole number.")
    if exam_date is None:
        errors.append("Pick the exam date.")
    elif exam_date < today:
        errors.append("The exam date is in the past. Pick today or a later date.")
    if errors:
        return None, errors
    return {"exam_name": exam, "goal_university": university, "goal_score": score_i or None, "goal_scale": scale_i, "exam_date": exam_date.isoformat()}, []


def save_goal(student_id: str, clean: dict[str, Any]) -> None:
    """Saves only the goal fields; every other part of the student's data is untouched."""
    update_student(student_id, **clean)


def describe(goal: dict[str, Any]) -> tuple[str, str]:
    """(big line, small line) for the sidebar goal card."""
    big = goal["exam"] + (f" · {goal['university']}" if goal["university"] else "")
    bits = []
    if goal["days"] is not None:
        bits.append("exam is today" if goal["days"] == 0 else f"{goal['days']} day{'s' if goal['days'] != 1 else ''} to go")
    if goal["score"]:
        bits.append(f"target {goal['score']}/{goal['scale']}")
    return big, " · ".join(bits)
