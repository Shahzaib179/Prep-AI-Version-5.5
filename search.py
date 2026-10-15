"""Global search (v5.6). Pure logic, no Streamlit: finds app pages, and the signed-in user's own content (mistakes, classes, assignments, quiz history; for tutors
their classes and question bank). Every result carries the page (route) it opens."""
from __future__ import annotations

from typing import Any

import navigation

# extra words that find a page (the page name itself always matches)
KEYWORDS = {
    "Dashboard": "home overview progress stats", "Today": "schedule agenda tasks plan",
    "Learn": "lesson study notes chapter topic explain", "Practice": "mcq questions quiz drill",
    "Exam": "timed test paper", "Mock Test": "mock full length sectioned blueprint negative marking",
    "Live Quiz": "live host join code realtime", "My Classes": "class tutor assignment homework join code deadline",
    "Published Quizzes": "shared quiz code tutor quiz", "Learning Games": "game quick mcq rapid fire fun",
    "Daily Challenge": "daily challenge streak", "Leaderboard": "rank ranking top xp",
    "Score Predictor": "predict score estimate target marks", "Mistakes Diary": "mistake wrong teach me revise errors",
    "History": "past results attempts quizzes trend", "AI Tutor": "ask doubt chat explain tutor ai",
    "Voice Tutor": "speak voice talk audio", "Research Agent": "research web search sources",
    "Study Plan": "plan calendar timetable schedule days exam date", "Merit Calculator": "merit aggregate calculate fsc matric mdcat marks",
    "Path Finder": "career path college university profile wizard", "Memory": "remember memories saved", "Settings": "profile theme colour color preferences language",
    "Tutor Dashboard": "create quiz publish students documents assignments question bank",
}
ICON = {r: i for _, items in navigation.STUDENT_NAV + navigation.TUTOR_NAV for r, i in items}


def _tokens(q: str) -> list[str]:
    return [t for t in (q or "").lower().split() if t]


def _hit(tokens: list[str], *fields: Any) -> bool:
    hay = " ".join(str(f or "") for f in fields).lower()
    return bool(tokens) and all(t in hay for t in tokens)


def _item(kind: str, title: str, detail: str, route: str, icon: str | None = None) -> dict[str, str]:
    return {"kind": kind, "title": title, "detail": detail, "route": route, "icon": icon or ICON.get(route, "search")}


def pages(query: str, is_tutor: bool) -> list[dict[str, str]]:
    toks = _tokens(query)
    found = []
    for r in navigation.routes(is_tutor):
        if _hit(toks, r, KEYWORDS.get(r, "")):
            rank = 0 if r.lower().startswith(toks[0]) else 1 if toks[0] in r.lower() else 2
            found.append((rank, _item("Page", r, "Open this page", r)))
    return [x for _, x in sorted(found, key=lambda t: t[0])]


def _clip(text: str, n: int = 90) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def content(query: str, user_id: str, is_tutor: bool, per_kind: int = 4) -> list[dict[str, str]]:
    """The user's own content that matches. Each source is isolated: a failing one never hides the others."""
    toks, out = _tokens(query), []
    if not toks or not user_id:
        return out

    def add(source):
        try:
            out.extend(source()[:per_kind])
        except Exception:        # search must never break a page
            pass

    if is_tutor:
        import bank, classes
        add(lambda: [_item("Class", c["name"], f"{c['members']} students · {c['assignments']} assignments", "Tutor Dashboard", "groups")
                     for c in classes.list_classes(user_id) if _hit(toks, c["name"])])
        add(lambda: [_item("Question", _clip(b.get("question") or b.get("question_text") or ""), f"{b.get('subject', '')} · {b.get('topic', '')}", "Tutor Dashboard", "quiz")
                     for b in bank.list_questions(user_id, search=" ".join(toks), limit=per_kind)])
        return out
    import classes, db, diary
    add(lambda: [_item("Mistake", _clip(m["question"]), f"{m['subject']} · {m['topic']}".strip(" ·"), "Mistakes Diary", "error_outline")
                 for m in diary.open_mistakes(user_id) if _hit(toks, m["question"], m["subject"], m["topic"], m["concept"])])
    add(lambda: [_item("Class", c["name"], f"Tutor {c['tutor_name']}", "My Classes", "groups") for c in classes.my_classes(user_id) if _hit(toks, c["name"], c["tutor_name"])])
    add(lambda: [_item("Assignment", a["title"], f"{a['class_name']} · {a['status'].replace('_', ' ')}", "My Classes", "assignment")
                 for a in classes.student_assignments(user_id) if _hit(toks, a["title"], a["class_name"])])
    add(lambda: [_item("History", f"{h['subject']}: {h['topic']}", f"{float(h['score'] or 0):.0f}% · {str(h['created_at'] or '')[:10]}", "History", "history")
                 for h in reversed(db.history(user_id, 100)) if _hit(toks, h["subject"], h["topic"])])
    return out


def search(query: str, user_id: str, is_tutor: bool) -> list[dict[str, str]]:
    q = (query or "").strip()
    if len(q) < 2:
        return []
    return pages(q, is_tutor)[:6] + content(q, user_id, is_tutor)
