"""Leaderboard from stored activity only.

Points = the XP each student has already earned (daily_activity.xp): 2 per answered question, 3 per correct answer, 10 per finished quiz,
20 for a perfect quiz, and the Daily Challenge bonus (config.XP_*). Practice, exams, mock tests, games and the daily challenge all write to that
one ledger, so a result is never counted twice. Periods: this week (today and the 6 days before) or all time.
Ties: more correct answers first, then the earlier sign-up, then the student id, so the order is always the same for the same data.
Names: first name plus last initial; anything that looks like an email or phone number is replaced by an anonymous label. Emails are never read.
Pure logic over the database (no Streamlit).
"""
from __future__ import annotations

import hashlib
import re
from datetime import timedelta
from typing import Any

import progress
from db_core import cached_read, connect

PERIODS = {"week": "This week", "all": "All time"}


def display_name(name: str | None, student_id: str) -> str:
    anon = "Student " + hashlib.sha1((student_id or "").encode("utf-8")).hexdigest()[:4].upper()
    name = " ".join((name or "").split())
    if not name or "@" in name or sum(ch.isdigit() for ch in name) >= 4 or not any(ch.isalpha() for ch in name):
        return anon
    parts = [re.sub(r"[^\w\-']", "", p) for p in name.split(" ")]
    parts = [p for p in parts if p]
    if not parts:
        return anon
    first = parts[0][:16]
    return first + (f" {parts[-1][0].upper()}." if len(parts) > 1 else "")


@cached_read(30)
def _totals(period: str) -> list[dict[str, Any]]:
    since = (progress.local_today() - timedelta(days=6)).isoformat() if period == "week" else "0000-00-00"
    with connect() as con:
        rows = con.execute("SELECT a.student_id, SUM(a.xp) AS points, SUM(a.correct) AS correct, SUM(a.questions) AS answered, SUM(a.quizzes) AS quizzes, "
                           "COALESCE(s.name,'') AS name, COALESCE(s.created_at,'') AS joined FROM daily_activity a LEFT JOIN students s ON s.id=a.student_id "
                           "WHERE a.day>=? GROUP BY a.student_id, s.name, s.created_at HAVING SUM(a.xp)>0", (since,)).fetchall()
    return [dict(r) for r in rows]


def ranking(period: str = "week") -> list[dict[str, Any]]:
    """Everyone with points in the period, best first, with a display name that is safe to show other students."""
    rows = sorted(_totals(period), key=lambda r: (-int(r["points"]), -int(r["correct"] or 0), r["joined"], r["student_id"]))
    return [{"rank": i, "student_id": r["student_id"], "name": display_name(r["name"], r["student_id"]), "points": int(r["points"]),
             "correct": int(r["correct"] or 0), "answered": int(r["answered"] or 0), "quizzes": int(r["quizzes"] or 0)} for i, r in enumerate(rows, start=1)]


def view(student_id: str, period: str = "week", top: int = 10) -> dict[str, Any]:
    """Top rows, the student's own row (even when outside the top), and the number of ranked students. The student_id is not exposed to the page."""
    rows = ranking(period)
    mine = next((r for r in rows if r["student_id"] == student_id), None)
    strip = lambda r: {k: v for k, v in r.items() if k != "student_id"} | {"is_me": r["student_id"] == student_id}   # noqa: E731
    return {"rows": [strip(r) for r in rows[:top]], "me": strip(mine) if mine else None, "count": len(rows), "period": period}
