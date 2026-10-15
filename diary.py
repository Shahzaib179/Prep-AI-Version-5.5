"""Mistakes Diary: every question the student answered wrongly and has not yet been taught or fixed.

A diary entry leaves the diary when the student (a) has been taught it and moves on to the next mistake, or (b) later answers that same question correctly.
Nothing is deleted: a taught mistake only gets a ``resolved_at`` stamp, so history and the raw answers stay intact.
Mistakes made in the learning games are never recorded (db.record_game_round), so they cannot appear here.
Pure logic over the database (no Streamlit).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from db_core import cached_read, connect
from progress import qhash

MAX_ROWS = 500       # safety cap on the rows read; the diary of one student never realistically gets near it


@cached_read(30)
def open_mistakes(student_id: str) -> list[dict[str, Any]]:
    """Open diary entries, newest first, one per question (the latest wrong answer), without questions answered correctly since."""
    with connect() as con:
        rows = con.execute("SELECT id,subject,topic,concept,question_text,wrong_answer,correct_answer,explanation,options_json,difficulty,created_at "
                           "FROM mistakes WHERE student_id=? AND resolved_at IS NULL ORDER BY id DESC LIMIT ?", (student_id, MAX_ROWS)).fetchall()
        texts = sorted({r["question_text"] for r in rows})
        last: dict[str, bool] = {}          # was the student's latest attempt at this question correct?
        for i in range(0, len(texts), 400):
            part = texts[i:i + 400]
            for q, ok in con.execute("SELECT question_text,is_correct FROM question_attempts WHERE student_id=? AND question_text IN (%s) ORDER BY id" % ",".join("?" * len(part)),
                                     (student_id, *part)).fetchall():
                last[qhash(q)] = bool(ok)
    fixed = {h for h, ok in last.items() if ok}
    out, seen = [], set(fixed)
    for r in rows:
        h = qhash(r["question_text"])
        if h in seen:
            continue
        seen.add(h)
        try:
            options = json.loads(r["options_json"] or "{}")
        except (TypeError, ValueError):
            options = {}
        out.append({"id": int(r["id"]), "subject": r["subject"] or "General", "topic": r["topic"] or "", "concept": r["concept"] or "", "question": r["question_text"],
                    "wrong": r["wrong_answer"] or "", "correct": r["correct_answer"] or "", "explanation": r["explanation"] or "",
                    "options": options if isinstance(options, dict) else {}, "difficulty": r["difficulty"] or "", "created_at": r["created_at"]})
    return out


def open_count(student_id: str) -> int:
    return len(open_mistakes(student_id))


def resolve(student_id: str, mistake_id: int) -> int:
    """Take a mistake (and every earlier copy of the same question) out of the diary. Returns rows stamped."""
    with connect() as con:
        cur = con.execute("UPDATE mistakes SET resolved_at=? WHERE student_id=? AND resolved_at IS NULL AND question_text=(SELECT question_text FROM mistakes WHERE id=? AND student_id=?)",
                          (datetime.utcnow().isoformat(), student_id, int(mistake_id), student_id))
        return int(cur.rowcount or 0)


def option_text(m: dict[str, Any], letter: str) -> str:
    """'B. Mitochondria' for a stored letter, or just what was stored when the options are unknown."""
    txt = (m.get("options") or {}).get(letter)
    return f"{letter}. {txt}" if txt else (letter or "No answer")


def teach_prompt(m: dict[str, Any]) -> str:
    return (f"Teach me this one mistake step by step, in simple words.\n"
            f"Subject: {m['subject']}  Topic: {m['topic'] or 'general'}\n"
            f"Question: {m['question']}\n"
            f"My answer: {option_text(m, m['wrong'])}\n"
            f"Correct answer: {option_text(m, m['correct'])}\n"
            f"Stored explanation: {m['explanation'] or 'none'}\n"
            "Explain: 1) why my answer is wrong, 2) why the correct answer is right, 3) the core concept in two or three lines, 4) one short memory trick, "
            "5) one quick check question I can answer in my head. Keep it under 250 words.")


def fallback_teaching(m: dict[str, Any]) -> str:
    """Used when the AI is unavailable: only what the app already stored, no invented content."""
    lines = [f"**Your answer:** {option_text(m, m['wrong'])}", f"**Correct answer:** {option_text(m, m['correct'])}"]
    lines.append(f"**Why:** {m['explanation']}" if m["explanation"] else "**Why:** no explanation was stored for this question. Open Learn or AI Tutor and ask about this topic.")
    lines.append("_The AI teacher could not be reached, so this is the saved explanation. Press **Teach me this mistake** again later for a full lesson._")
    return "\n\n".join(lines)
