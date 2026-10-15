"""Practice-based score estimate shown on the dashboard.

Prep.AI has no official score predictor, so this is deliberately simple and honest: the student's real accuracy over answered
questions, scaled to the exam's marks, with a range that widens when there are few answers (Wilson interval). It is shown
only after SCORE_MIN_ANSWERS answered questions and is always labelled an estimate, never an official MDCAT prediction.
Pure functions (no Streamlit, no database).
"""
from __future__ import annotations

import math
from typing import Any

from config import SCORE_MIN_ANSWERS, SCORE_SCALE

Z80 = 1.2816   # two-sided 80% interval


def wilson(correct: int, total: int, z: float = Z80) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 1.0
    p = correct / total
    d = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / d
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def estimate(answered: int, correct: int, scale: int = SCORE_SCALE, min_answers: int = SCORE_MIN_ANSWERS) -> dict[str, Any]:
    answered, correct = max(0, int(answered)), max(0, min(int(correct), int(answered)))
    if answered < min_answers:
        return {"ready": False, "answered": answered, "needed": min_answers - answered, "scale": scale, "min_answers": min_answers}
    lo, hi = wilson(correct, answered)
    return {"ready": True, "answered": answered, "needed": 0, "scale": scale, "min_answers": min_answers,
            "accuracy": round(100 * correct / answered, 1), "score": round(scale * correct / answered),
            "low": round(scale * lo), "high": round(scale * hi)}


def trend(rows: list[tuple[str, int, int]], scale: int = SCORE_SCALE, min_answers: int = SCORE_MIN_ANSWERS) -> list[tuple[str, float]]:
    """Running estimate after each practice day: rows are (day, answered, correct) in date order. Days before the cumulative answer count reaches
    ``min_answers`` are left out (no estimate yet), so the line never starts from a guess. Uses the same formula as estimate()."""
    out: list[tuple[str, float]] = []
    answered = correct = 0
    for day, q, c in sorted(rows):
        answered += max(0, int(q))
        correct += max(0, int(c))
        if answered >= min_answers:
            out.append((day, round(scale * min(correct, answered) / answered, 1)))
    return out


def recommendations(est: dict[str, Any], target: int | None, weak: list[dict[str, Any]], revisions_due: int, answered_today: int, goal: int) -> list[str]:
    """Plain advice derived only from the numbers passed in; empty when there is nothing real to say."""
    tips: list[str] = []
    if not est.get("ready"):
        tips.append(f"Answer {est['needed']} more question(s) to unlock your estimate.")
        return tips
    if target:
        gap = target - est["score"]
        if gap > 0:
            need = 100 * target / est["scale"]
            tips.append(f"Your target needs about {need:.0f}% accuracy; you are at {est['accuracy']:.0f}%.")
        else:
            tips.append("You are at or above your target on practice so far. Keep your accuracy steady on new questions.")
    for w in weak[:2]:
        tips.append(f"Practise {w['subject']} → {w['topic']} (mastery {w['mastery_score']:.0f}%).")
    if revisions_due:
        tips.append(f"Revise the {revisions_due} topic{'s' if revisions_due != 1 else ''} that are due.")
    if answered_today < goal:
        tips.append(f"Answer {goal - answered_today} more question(s) today to reach your daily goal.")
    return tips
