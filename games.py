"""Learning games: real MCQs, real scoring, no invented data.

A game round earns XP and keeps the streak (db.record_game_round) but is NOT part of student performance: no quiz history, no mistakes, no mastery,
no score estimate. This module adds the game layer: which questions to use, and one stored result per finished game (table game_results).
Questions come from the tutor/student question bank first, then the AI (optional callback), then the built-in starter set (evals/golden_questions.json),
so the games work offline. Nothing here awards extra XP: the leaderboard counts the one XP ledger, so nothing is counted twice.
Pure logic over the database (no Streamlit).
"""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Callable

import bank
import daily
import progress
from db_core import cached_read, connect

SUBJECTS = ["Biology", "Chemistry", "Physics", "English"]
GAMES: dict[str, dict[str, Any]] = {
    "quick": {"title": "Quick MCQ Challenge", "icon": "bolt", "per_q": 10, "counts": (5, 20, 10),
              "short": "10 seconds per question",
              "blurb": "You choose how many MCQs (5 to 20). One question at a time, 10 seconds each. If the time runs out the question is skipped and the next one appears."},
    "rapid": {"title": "Rapid Fire", "icon": "timer", "total": 60, "pool": 40,
              "short": "60 seconds, as many as you can",
              "blurb": "60 seconds on the clock. Answer as many MCQs as you can: every answer brings the next question straight away."},
}
LEGACY_TITLES = {"sprint": "Subject Sprint (retired)"}      # results saved by v5.2 stay in history under their old name
MIN_PLAYABLE = 5     # fewer real questions than this and the game says so instead of running a tiny round
GRACE_SEC = 0.8      # network allowance: an answer that reaches the server this late after its deadline still counts


def title_of(game: str) -> str:
    return GAMES.get(game, {}).get("title") or LEGACY_TITLES.get(game, game)


# ------------------------------------------------------------------ the timed engine (pure: the caller passes the clock)
def new_run(game: str, questions: list[dict[str, Any]], subject: str, now: float, uid: str = "") -> dict[str, Any]:
    """State of one play. Quick: ``per_q`` seconds for each question. Rapid: ``total`` seconds for the whole round."""
    g = GAMES[game]
    return {"game": game, "subject": subject, "uid": uid, "questions": list(questions), "idx": 0, "answers": {}, "start": now, "q_start": now,
            "per_q": g.get("per_q", 0), "total": g.get("total", 0), "done": False, "end": None, "exhausted": False, "saved": None}


def deadline(run: dict[str, Any]) -> float:
    return run["q_start"] + run["per_q"] if run["game"] == "quick" else run["start"] + run["total"]


def remaining(run: dict[str, Any], now: float) -> float:
    return max(0.0, deadline(run) - now)


def _finish(run: dict[str, Any], now: float) -> None:
    run["done"] = True
    run["end"] = min(now, run["start"] + run["total"]) if run["game"] == "rapid" else now


def tick(run: dict[str, Any], now: float) -> bool:
    """Apply the clock. Quick: every question whose time ran out is skipped (also several at once if the page was away). Rapid: ends the round at 60 s. True if done."""
    if run["done"]:
        return True
    if run["game"] == "quick":
        n = len(run["questions"])
        while not run["done"] and now > run["q_start"] + run["per_q"]:
            run["answers"][run["idx"]] = None
            run["idx"] += 1
            run["q_start"] += run["per_q"]
            if run["idx"] >= n:
                _finish(run, run["q_start"])
    elif now >= run["start"] + run["total"]:
        _finish(run, now)
    return run["done"]


def submit(run: dict[str, Any], letter: str, now: float) -> bool:
    """Record the answer to the current question if it arrived in time (server clock, plus GRACE_SEC). Returns whether it counted."""
    if run["done"]:
        return False
    if now > deadline(run) + GRACE_SEC:
        tick(run, now)
        return False
    i = run["idx"]
    run["answers"][i] = letter
    run["idx"] += 1
    run["q_start"] = now
    if run["idx"] >= len(run["questions"]):
        run["exhausted"] = run["game"] == "rapid"
        _finish(run, now)
    return True


def abort(run: dict[str, Any], now: float) -> None:
    _finish(run, now)


def outcome(run: dict[str, Any]) -> dict[str, Any]:
    """What to store: Quick = every question (unanswered ones are skipped); Rapid = only the questions that were answered."""
    served = list(range(len(run["questions"]))) if run["game"] == "quick" else list(range(run["idx"]))
    qs = [run["questions"][i] for i in served]
    answers = {j: run["answers"][i] for j, i in enumerate(served) if run["answers"].get(i)}
    correct = sum(1 for j, q in enumerate(qs) if answers.get(j) == str(q.get("answer", "")).strip())
    taken = int(round((run["end"] if run["end"] is not None else run["q_start"]) - run["start"]))
    return {"questions": qs, "answers": answers, "correct": correct, "answered": len(answers), "total": len(qs), "taken": max(0, taken),
            "limit": run["total"] or run["per_q"] * len(run["questions"]), "timed_out": run["game"] == "rapid" and not run["exhausted"]}


def _subject_pool(student_id: str, subject: str, need: int, generate: Callable[[str, int], list[dict[str, Any]]] | None, rng: random.Random) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen_now: set[str] = set()
    unseen = progress.seen_hashes(student_id)

    def add(pool: list[dict[str, Any]]) -> None:
        pool = [c for c in (daily._clean(q, subject) for q in pool) if c]      # same validation as the daily challenge
        rng.shuffle(pool)
        pool.sort(key=lambda c: progress.qhash(c["question"]) in unseen)       # questions the student has not met come first (stable sort keeps the shuffle)
        for c in pool:
            h = progress.qhash(c["question"])
            if h not in seen_now and len(out) < need:
                seen_now.add(h)
                out.append(c)

    add(bank.pick_for_student(student_id, subject, need * 2, seed=rng.random()))
    if len(out) < need:
        add([g for g in daily._golden() if g.get("subject") == subject])
    if len(out) < need and generate:
        try:
            add(generate(subject, need - len(out)) or [])
        except Exception:  # noqa: BLE001 - AI trouble must never block a game
            pass
    return out


def build_questions(student_id: str, subject: str, n: int, generate: Callable[[str, int], list[dict[str, Any]]] | None = None, seed: Any = None) -> list[dict[str, Any]]:
    """``n`` distinct, validated questions. subject 'Mixed' spreads them over the four standard subjects. May return fewer than n when the pools are small."""
    rng = random.Random(seed)
    if subject != "Mixed":
        return _subject_pool(student_id, subject, n, generate, rng)
    share = {s: n // len(SUBJECTS) + (1 if i < n % len(SUBJECTS) else 0) for i, s in enumerate(SUBJECTS)}
    out: list[dict[str, Any]] = []
    for s, k in share.items():
        out += _subject_pool(student_id, s, k, generate, rng)
    rng.shuffle(out)
    return out


def record_result(student_id: str, game: str, subject: str, correct: int, total: int, taken_sec: int | None, quiz_id: int | None = None) -> bool:
    """Store one finished game. Older versions stored a quiz id (unique per student); new rounds have none and are saved once by the caller."""
    with connect() as con:
        cur = con.execute("INSERT INTO game_results(student_id,game,subject,correct,total,taken_sec,quiz_id,day,created_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(student_id,quiz_id) DO NOTHING",
                          (student_id, game, subject, int(correct), int(total), taken_sec, quiz_id, progress.local_today().isoformat(), datetime.utcnow().isoformat()))
        return cur.rowcount == 1


@cached_read(30)
def history(student_id: str, limit: int = 8) -> list[dict[str, Any]]:
    with connect() as con:
        rows = con.execute("SELECT game,subject,correct,total,taken_sec,created_at FROM game_results WHERE student_id=? ORDER BY id DESC LIMIT ?", (student_id, int(limit))).fetchall()
    return [dict(r) for r in rows]


@cached_read(30)
def best(student_id: str) -> dict[str, dict[str, Any]]:
    """Best result per game. Rapid Fire: most correct answers (then accuracy). Others: highest accuracy, then fastest."""
    with connect() as con:
        rows = con.execute("SELECT game,correct,total,taken_sec FROM game_results WHERE student_id=? AND total>0", (student_id,)).fetchall()
    top: dict[str, dict[str, Any]] = {}
    for r in rows:
        r = dict(r)
        acc = r["correct"] / r["total"]
        key = (r["correct"], acc) if r["game"] == "rapid" else (acc, -(r["taken_sec"] if r["taken_sec"] is not None else 10 ** 6))
        if r["game"] not in top or key > top[r["game"]]["_k"]:
            top[r["game"]] = {**r, "_k": key}
    return {g: {k: v for k, v in r.items() if k != "_k"} for g, r in top.items()}


def played_count(student_id: str) -> int:
    with connect() as con:
        return int(con.execute("SELECT COUNT(*) FROM game_results WHERE student_id=?", (student_id,)).fetchone()[0])
