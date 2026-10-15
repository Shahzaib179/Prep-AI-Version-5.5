"""Data behind the dashboard: today's checklist, schedule, subject performance and recent activity.

Everything here is read from data the app already stores (progress, mastery, revisions, mistakes, classes, the saved study
plan, daily challenge). The only new storage is the tick boxes for study-plan sessions (table daily_tasks).
No Streamlit and no AI calls, so it is fast and testable.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

import classes
import config
import daily
import navigation
import progress
from db import dashboard_stats, due_revisions, history, topic_mastery
from db_core import cached_read, connect

STANDARD_SUBJECTS = ("Biology", "Chemistry", "Physics", "English")
SHORT = {"Biology": "BIO", "Chemistry": "CHE", "Physics": "PHY", "English": "ENG", "Logical Reasoning": "LR"}


# ------------------------------------------------------------------ study plan -> today's sessions
@cached_read(30)
def latest_plan(student_id: str) -> dict[str, Any] | None:
    with connect() as con:
        r = con.execute("SELECT id, exam_name, exam_date, plan_json, created_at FROM study_plans WHERE student_id=? ORDER BY id DESC LIMIT 1", (student_id,)).fetchone()
    if not r:
        return None
    try:
        days = json.loads(r["plan_json"] or "[]")
    except (TypeError, ValueError):
        days = []
    return {"id": int(r["id"]), "exam_name": r["exam_name"], "exam_date": r["exam_date"], "created_at": r["created_at"], "days": days if isinstance(days, list) else []}


def plan_today(student_id: str, today: date | None = None) -> dict[str, Any] | None:
    """The saved plan's day for today (Day 1 = the day the plan was made). None when there is no plan or it has ended."""
    plan = latest_plan(student_id)
    if not plan or not plan["days"]:
        return None
    today = today or progress.local_today()
    try:
        start = (datetime.fromisoformat(plan["created_at"]) + timedelta(minutes=config.PROGRESS_TZ_OFFSET_MIN)).date()   # created_at is UTC; "today" is the student's local day
    except (TypeError, ValueError):
        return None
    idx = (today - start).days
    if not 0 <= idx < len(plan["days"]):
        return {"plan_id": plan["id"], "ended": idx >= len(plan["days"]), "sessions": [], "day_no": idx + 1, "total_days": len(plan["days"])}
    day = plan["days"][idx] if isinstance(plan["days"][idx], dict) else {}
    sessions = [s for s in (day.get("sessions") or []) if isinstance(s, dict)]
    return {"plan_id": plan["id"], "ended": False, "label": day.get("day") or f"Day {idx + 1}", "day_no": idx + 1, "total_days": len(plan["days"]), "sessions": sessions}


# ------------------------------------------------------------------ tick boxes
def done_keys(student_id: str, day: date) -> set[str]:
    with connect() as con:
        return {r[0] for r in con.execute("SELECT task_key FROM daily_tasks WHERE student_id=? AND day=?", (student_id, day.isoformat())).fetchall()}


def set_task_done(student_id: str, day: date, key: str, done: bool) -> None:
    with connect() as con:
        if done:
            con.execute("INSERT INTO daily_tasks(student_id,day,task_key,done_at) VALUES(?,?,?,?) ON CONFLICT(student_id,day,task_key) DO NOTHING",
                        (student_id, day.isoformat(), key, datetime.utcnow().isoformat()))
        else:
            con.execute("DELETE FROM daily_tasks WHERE student_id=? AND day=?  AND task_key=?", (student_id, day.isoformat(), key))


# ------------------------------------------------------------------ checklist
def todays_tasks(student_id: str, today: date | None = None) -> list[dict[str, Any]]:
    """Checklist items. kind 'auto' = completed by actually doing it (measured from real activity); 'plan' = a tick box for a study-plan session."""
    today = today or progress.local_today()
    p = progress.get_progress(student_id, today)
    tasks: list[dict[str, Any]] = [{"key": "goal", "kind": "auto", "title": f"Answer {p['goal']} questions", "detail": f"{p['today_questions']} of {p['goal']} answered today",
                                    "done": bool(p["goal_done"]), "page": "Practice"}]
    due = due_revisions(student_id)
    if due:
        tasks.append({"key": "revision", "kind": "auto", "title": f"Revise {len(due)} due topic{'s' if len(due) != 1 else ''}", "detail": ", ".join(f"{d['topic']}" for d in due[:2]),
                      "done": False, "page": "Practice"})
    open_mistakes = len(progress.retakeable_mistakes(student_id, 20))
    if open_mistakes:
        tasks.append({"key": "mistakes", "kind": "auto", "title": f"Retake {open_mistakes} mistake{'s' if open_mistakes != 1 else ''}", "detail": "Questions you got wrong and have not fixed", "done": False, "page": "Today"})
    tasks.append({"key": "daily", "kind": "auto", "title": "Daily Challenge", "detail": "5 questions, same for everyone today",
                  "done": daily.result_for(student_id, today) is not None, "page": "Daily Challenge"})
    pending = [a for a in classes.student_assignments(student_id) if a["status"] in ("overdue", "due_soon")]
    if pending:
        tasks.append({"key": "assignments", "kind": "auto", "title": f"{len(pending)} assignment{'s' if len(pending) != 1 else ''} to finish", "detail": pending[0]["title"], "done": False, "page": "My Classes"})
    plan = plan_today(student_id, today)
    if plan and plan["sessions"]:
        ticked = done_keys(student_id, today)
        for n, s in enumerate(plan["sessions"]):
            key = f"plan:{plan['plan_id']}:{plan['day_no']}:{n}"
            tasks.append({"key": key, "kind": "plan", "title": f"{s.get('subject', '')}: {s.get('topic', 'Study session')}".strip(": "),
                          "detail": f"{s.get('minutes', 0)} min · {s.get('activity', '')}", "done": key in ticked, "page": "Study Plan"})
    return tasks


def finish_line_tasks(student_id: str, today: date | None = None) -> list[dict[str, Any]]:
    """The four fixed items of Today's Finish Line, always in this order: daily question goal, due revisions, open mistakes, Daily Challenge.
    Revise / Retake count as done when there is nothing due or open (the work is complete by definition), and say so. Study-plan sessions and
    tutor assignments belong to Today's Schedule, not here."""
    today = today or progress.local_today()
    p = progress.get_progress(student_id, today)
    due = due_revisions(student_id)
    n_mistakes = len(progress.retakeable_mistakes(student_id, 20))
    return [
        {"key": "goal", "kind": "auto", "title": f"Answer {p['goal']} questions", "detail": f"{p['today_questions']} of {p['goal']} answered today", "done": bool(p["goal_done"]), "page": "Practice"},
        {"key": "revision", "kind": "auto", "title": f"Revise {len(due)} due topic{'s' if len(due) != 1 else ''}" if due else "Revise due topics",
         "detail": ", ".join(f"{d['topic']}" for d in due[:2]) if due else "Nothing due today", "done": not due, "page": "Practice"},
        {"key": "mistakes", "kind": "auto", "title": f"Retake {n_mistakes} mistake{'s' if n_mistakes != 1 else ''}" if n_mistakes else "Retake mistakes",
         "detail": "Questions you got wrong and have not fixed" if n_mistakes else "No open mistakes", "done": not n_mistakes, "page": "Today"},
        {"key": "daily", "kind": "auto", "title": "Daily Challenge", "detail": "5 questions, same for everyone today", "done": daily.result_for(student_id, today) is not None, "page": "Daily Challenge"},
    ]


def task_progress(tasks: list[dict[str, Any]]) -> tuple[int, int]:
    return sum(1 for t in tasks if t["done"]), len(tasks)


# ------------------------------------------------------------------ schedule
ROUTE_ICON = {route: icon for _, items in navigation.STUDENT_NAV for route, icon in items}      # every sidebar tab keeps its own icon


def tab_icon(route: str) -> str:
    return ROUTE_ICON.get(route, "event")


def schedule(student_id: str, today: date | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Today's study-plan sessions and the next assignment deadlines, plus ``items``: ONE list for the Schedule card. Each item names the sidebar tab it belongs to
    (``route``) and that tab's icon; study-plan sessions can be marked Done (``can_done``), tutor work is finished by doing it. Nothing is invented: no data, no items."""
    today = today or progress.local_today()
    plan = plan_today(student_id, today)
    ticked = done_keys(student_id, today) if plan and plan.get("sessions") else set()
    sessions = [{"title": f"{s.get('subject', '')}: {s.get('topic', '')}".strip(": "), "minutes": s.get("minutes", 0), "activity": s.get("activity", ""),
                 "key": f"plan:{plan['plan_id']}:{plan['day_no']}:{n}", "done": f"plan:{plan['plan_id']}:{plan['day_no']}:{n}" in ticked} for n, s in enumerate(plan["sessions"])] if plan else []
    assigned = []
    for a in classes.student_assignments(student_id, now):
        if a["status"] in ("overdue", "due_soon", "open") and a.get("due_at"):
            assigned.append({"title": a["title"], "class": a["class_name"], "due_at": a["due_at"], "status": a["status"], "kind": a.get("kind", "quiz")})
    assigned.sort(key=lambda a: a["due_at"])
    assigned = assigned[:6]
    items = [{"kind": "plan", "key": x["key"], "title": x["title"], "detail": f"{x['minutes']} min · {x['activity']}".strip(" ·"), "route": "Study Plan", "icon": tab_icon("Study Plan"),
              "done": x["done"], "can_done": True, "due_at": None, "status": ""} for x in sessions]
    items += [{"kind": a["kind"], "key": f"class:{n}", "title": a["title"], "detail": f"{a['class']} · {'PDF assignment' if a['kind'] == 'pdf' else 'Quiz'}", "route": "My Classes",
               "icon": tab_icon("My Classes"), "done": False, "can_done": False, "due_at": a["due_at"], "status": a["status"]} for n, a in enumerate(assigned)]
    return {"plan": plan, "sessions": sessions, "assignments": assigned, "items": items}


# ------------------------------------------------------------------ performance
def subject_performance(student_id: str) -> list[dict[str, Any]]:
    """Per subject: mastery (answers-weighted mean of the existing topic mastery), pooled accuracy, strongest/weakest topic. No data -> has_data False."""
    topics = topic_mastery(student_id)
    out = []
    names = list(STANDARD_SUBJECTS) + sorted({t["subject"] for t in topics if t["subject"] not in STANDARD_SUBJECTS and t["subject"]})
    for name in names:
        rows = [t for t in topics if t["subject"] == name]
        n = sum(t["attempts"] for t in rows)
        if not rows or not n:
            out.append({"subject": name, "short": SHORT.get(name, name[:3].upper()), "has_data": False, "attempts": 0})
            continue
        mastery = sum(t["mastery_score"] * t["attempts"] for t in rows) / n
        acc = sum(t["accuracy"] * t["attempts"] for t in rows) / n
        solid = [t for t in rows if t["enough_data"]]
        out.append({"subject": name, "short": SHORT.get(name, name[:3].upper()), "has_data": True, "attempts": n, "mastery": round(mastery, 1), "accuracy": round(acc, 1),
                    "weakest": min(solid, key=lambda t: t["mastery_score"])["topic"] if solid else None,
                    "strongest": max(solid, key=lambda t: t["mastery_score"])["topic"] if solid else None})
    return out


def recent_quizzes(student_id: str, limit: int = 4) -> list[dict[str, Any]]:
    return [{"subject": h["subject"], "topic": h["topic"], "score": float(h["score"] or 0), "correct": h["correct"], "total": h["total"], "when": (h["created_at"] or "")[:10]}
            for h in history(student_id, limit)]


def days_to_exam(exam_date: str | None, today: date | None = None) -> int | None:
    try:
        d = (date.fromisoformat(exam_date or "") - (today or progress.local_today())).days
    except ValueError:
        return None
    return d if d >= 0 else None


def overview(student_id: str) -> dict[str, Any]:
    return dashboard_stats(student_id)
