"""Career Path Finder: the step-by-step student profile (pure logic, no Streamlit).

The steps follow the Undergraduate Admission Counselling Guide: A academic background, B interests and preferred degrees, C skills and personality,
D career goals, E university and affordability, F commitment and readiness, then the stream-specific questions, the weighted comparison of the
student's top options, and the final admission checklist.

Nothing is invented here. The weighted comparison is plain arithmetic over the student's own 1-5 ratings; the recommendation card only repeats what the
student entered (their degrees, their universities, their backup) next to the degree programs the verified knowledge base matches to their stream.
The result is a counselling aid, not a prediction of admission.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from db_core import connect

# ------------------------------------------------------------------ the weighted comparison (section 4 of the guide)
CRITERIA: list[tuple[str, str, int]] = [
    ("interest", "Personal interest", 20), ("aptitude", "Academic aptitude and eligibility", 20), ("career", "Career opportunities", 20),
    ("afford", "Affordability", 15), ("quality", "University quality and accreditation", 10), ("lifestyle", "Work environment and lifestyle fit", 10),
    ("training", "Willingness to complete the training", 5),
]
MAX_OPTIONS = 3
DISCLAIMER = ("This is a counselling aid, not a scientifically validated prediction. A high score does not help if you are ineligible, "
              "cannot afford the program, or do not understand its requirements.")

CHECKLIST = [
    "The degree matches my interests and abilities.",
    "I meet the subject and marks requirements.",
    "I know which entrance tests I need.",
    "The university and program are accredited (checked on the official site).",
    "I have reviewed the full cost and the scholarships.",
    "The curriculum, internships and career paths are clear to me.",
    "I have shortlisted at least two alternative programs or universities.",
    "I know the application deadlines and have my documents ready.",
]

# ------------------------------------------------------------------ stream-specific questions (section 2 of the guide)
STREAM_QUESTIONS: dict[str, list[str]] = {
    "Pre-Medical": ["Do you enjoy biology and understanding the human body?", "Are you comfortable caring for patients and taking responsibility?",
                    "Have you explored alternatives (pharmacy, nursing, allied health)?", "Are you prepared for the competitive admissions (MDCAT)?"],
    "Pre-Engineering": ["Do you enjoy math, physics and technical problem-solving?", "Would you prefer mechanical, electrical, civil, chemical or mechatronics?",
                        "Do you enjoy practical projects and hands-on work?", "Have you checked accreditation and job opportunities?"],
    "ICS (Computer Science)": ["Do you enjoy programming, logic and problem-solving?", "Have you tried coding or a small project?",
                               "Are you interested in software, AI, cybersecurity or data science?", "Do you enjoy continuous learning as technology changes?"],
    "OTHER": ["Do you enjoy accounting, business, economics, writing or creative work?", "Are you interested in finance, marketing, HR, teaching, law or media?",
              "Do you prefer working with people, information, money or ideas?", "Have you checked the degree options and career paths?"],
}
ANSWERS = ["Yes", "Somewhat", "No"]


def stream_questions(stream: str) -> list[str]:
    return STREAM_QUESTIONS.get(stream) or STREAM_QUESTIONS["OTHER"]


# ------------------------------------------------------------------ weighted scoring
def _clamp(v: Any) -> int:
    try:
        return max(1, min(5, int(v)))
    except (TypeError, ValueError):
        return 3                                            # the slider starts in the middle: an untouched criterion counts as neutral


def weighted_percent(scores: dict[str, Any]) -> float:
    """0-100: each 1-5 rating is worth (rating / 5) of its weight; the weights add up to 100."""
    return round(sum(w * _clamp(scores.get(key)) / 5 for key, _, w in CRITERIA), 1)


def rank_options(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Named options only, best first. Ties keep the order the student typed them in."""
    rows = [{"name": str(o.get("name", "")).strip(), "scores": {k: _clamp((o.get("scores") or {}).get(k)) for k, _, _ in CRITERIA}} for o in (options or [])[:MAX_OPTIONS]]
    rows = [r for r in rows if r["name"]]
    for r in rows:
        r["percent"] = weighted_percent(r["scores"])
    return sorted(rows, key=lambda r: -r["percent"])


# ------------------------------------------------------------------ profile -> what Path Finder consumes
def _lines(text: Any, limit: int = 5) -> list[str]:
    return [ln.strip() for ln in str(text or "").replace(";", "\n").splitlines() if ln.strip()][:limit]


def to_pf_profile(data: dict[str, Any]) -> dict[str, Any]:
    """The profile dict Path Finder's pipeline already understands, plus the new counselling answers (they reach the prompt as extra profile facts)."""
    def num(key: str) -> float | None:
        try:
            v = float(data.get(key) or 0)
        except (TypeError, ValueError):
            return None
        return v or None
    goal = " ".join(x for x in (str(data.get("career_aim", "")).strip(), "Backup if not admitted: " + str(data["backup"]).strip() if data.get("backup") else "") if x)
    prof: dict[str, Any] = {
        "level": data.get("level") or "", "stream": data.get("stream") or "", "interests": list(data.get("interests") or []),
        "matric_pct": num("matric_pct"), "fsc_pct": num("fsc_pct"), "test_pct": num("test_pct"), "province": data.get("province") or "",
        "family_income": num("family_income"), "annual_budget": num("annual_budget"), "goals": goal,
    }
    extra = {
        "strong_subjects": data.get("strong_subjects"), "weak_subjects": data.get("weak_subjects"), "entrance_tests": data.get("entrance_tests"),
        "applying": data.get("applying"), "degrees_considering": [d for d in (data.get(f"degree{i}") for i in (1, 2, 3)) if d], "why_these_degrees": data.get("why_degrees"),
        "activities_liked": data.get("activities"), "strengths": data.get("strengths"), "preferred_work_style": data.get("style"),
        "work_sector": data.get("sector"), "matters_most": data.get("priority"), "where_to_work": data.get("location"), "further_study": data.get("further_study"),
        "universities_considering": _lines(data.get("universities")), "family_can_fund_program": data.get("family_support"), "needs_financial_aid": data.get("aid"),
        "will_study_in_another_city": data.get("other_city"), "ready_for_long_study": data.get("ready_years"), "biggest_concern": data.get("concern"),
        "stream_specific_answers": data.get("stream_answers"),
        "own_comparison": [{"option": r["name"], "weighted_percent": r["percent"]} for r in rank_options(data.get("options") or [])],
    }
    prof.update({k: v for k, v in extra.items() if v not in (None, "", [], {})})
    return {k: v for k, v in prof.items() if v not in (None, "", [], {})} | {"interests": prof["interests"]}


def missing_for_run(data: dict[str, Any]) -> list[str]:
    """What the student should still fill in before the run is useful (the run itself never needs more than a stream)."""
    gaps = []
    if not data.get("stream"):
        gaps.append("your intermediate stream (step 1)")
    if not (data.get("interests") or any(data.get(f"degree{i}") for i in (1, 2, 3))):
        gaps.append("an interest or at least one degree you are considering (step 2)")
    if not data.get("fsc_pct"):
        gaps.append("your FSc / A-Level percentage so far (step 1), so eligibility can be checked")
    return gaps


def recommendation(data: dict[str, Any], matched_programs: list[dict[str, Any]]) -> dict[str, Any]:
    """The closing card of the guide: 3 degree options, the universities to shortlist and 1 backup plan.
    Degrees come from the student's own ranking first, then from knowledge-base programs that fit the stream; universities and the backup are the student's own words."""
    ranked = rank_options(data.get("options") or [])
    degrees = [{"name": r["name"], "note": f"your weighted score {r['percent']:.0f}%", "own": True} for r in ranked]
    seen = {d["name"].lower() for d in degrees}
    for p in matched_programs:
        if len(degrees) >= 3:
            break
        if p["name"].lower() not in seen:
            degrees.append({"name": p["name"], "note": f"fits your {p.get('match_reason') or 'profile'} (verified program list)", "own": False})
    return {"degrees": degrees[:3], "universities": _lines(data.get("universities"))[:5], "backup": str(data.get("backup") or "").strip()}


# ------------------------------------------------------------------ saving (the student can leave and continue later)
NOT_SAVED = ("family_income",)          # sensitive and optional: asked again when needed, never stored


def save(student_id: str, data: dict[str, Any], step: int) -> None:
    clean = {k: v for k, v in data.items() if k not in NOT_SAVED}
    now = datetime.utcnow().isoformat()
    with connect() as con:
        con.execute("INSERT INTO career_profiles(student_id,data_json,step,updated_at) VALUES(?,?,?,?) "
                    "ON CONFLICT(student_id) DO UPDATE SET data_json=excluded.data_json, step=excluded.step, updated_at=excluded.updated_at",
                    (student_id, json.dumps(clean, ensure_ascii=False), int(step), now))


def load(student_id: str) -> tuple[dict[str, Any], int]:
    with connect() as con:
        r = con.execute("SELECT data_json, step FROM career_profiles WHERE student_id=?", (student_id,)).fetchone()
    if not r:
        return {}, 0
    try:
        data = json.loads(r["data_json"] or "{}")
    except (TypeError, ValueError):
        data = {}
    return (data if isinstance(data, dict) else {}), int(r["step"] or 0)


def clear(student_id: str) -> None:
    with connect() as con:
        con.execute("DELETE FROM career_profiles WHERE student_id=?", (student_id,))
