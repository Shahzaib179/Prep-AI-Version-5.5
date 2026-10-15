"""Learning Games page: Quick MCQ Challenge (you pick 5-20 MCQs, 10 seconds each) and Rapid Fire (as many MCQs as you can in 60 seconds).

Real questions only (see games.build_questions). The countdown runs in a small fragment that reruns every half second; the server clock decides what counts
(games.submit / games.tick), so a slow or stale browser tab cannot add time. Finished rounds are stored as a normal quiz (history, mastery, XP, streak)
plus one game_results row.
"""
from __future__ import annotations

import math
import time
from typing import Any, Callable

import streamlit as st

import db
import games
import leaderboard_pages
import progress
import question_tools as qt
import ui_kit as k
from html import escape as esc
from quiz_runtime import clock
from ui import go_to, hero

KEY = "game_run"
TICK = 0.5


# ------------------------------------------------------------------ starting
def _start(student_id: str, game: str, subject: str, n: int, generate: Callable[[str, int], list[dict[str, Any]]] | None) -> None:
    g = games.GAMES[game]
    with st.spinner("Picking questions..."):
        if game == "quick":
            qs = games.build_questions(student_id, subject, n, generate)
        else:
            qs = games.build_questions(student_id, subject, g["pool"], None)        # no AI wait in a 60-second game: bank + starter set only
    if len(qs) < games.MIN_PLAYABLE:
        st.error(f"Only {len(qs)} question(s) are available for {subject} right now, so this game cannot start. Ask your tutor to share more questions, or try another subject.")
        return
    uid = f"{int(time.time() * 1000)}"
    qs = [qt.shuffle_options(q, f"{student_id}:{uid}:{progress.qhash(q['question'])}") for q in qs]   # same questions, options in a fresh order each play
    st.session_state[KEY] = games.new_run(game, qs, subject, time.time(), uid)
    st.rerun()


# ------------------------------------------------------------------ playing
def _answer(letter: str) -> None:
    run = st.session_state.get(KEY)
    if run:
        games.submit(run, letter, time.time())


def _quit() -> None:
    st.session_state.pop(KEY, None)


@st.fragment(run_every=TICK)
def _play() -> None:
    run = st.session_state.get(KEY)
    if not run or run["done"] or games.tick(run, time.time()):
        st.rerun()
        return
    now = time.time()
    left = games.remaining(run, now)
    q = run["questions"][run["idx"]]
    g = games.GAMES[run["game"]]
    secs = math.ceil(left)
    frac = 100 * left / (run["per_q"] or run["total"])
    if run["game"] == "quick":
        head = f"Question {run['idx'] + 1} of {len(run['questions'])}"
        side = f"{sum(1 for i, a in run['answers'].items() if a)} answered"
    else:
        ok = sum(1 for i, a in run["answers"].items() if a and a == str(run["questions"][i].get("answer", "")).strip())
        head = f"Question {run['idx'] + 1}"
        side = f"{ok} correct · {run['idx']} answered"
    st.markdown(f'<div class="pp-play"><div class="pp-timer"><div><small>{esc(g["title"])} · {esc(run["subject"])}</small><div>{esc(head)} · {esc(side)}</div></div>'
                f'<div class="big{" low" if secs <= (3 if run["game"] == "quick" else 10) else ""}" aria-live="off">{secs}s</div></div>'
                f'<div class="pp-bar {"err" if secs <= (3 if run["game"] == "quick" else 10) else ""}" role="img" aria-label="Time left"><i style="width:{frac:.0f}%"></i></div>'
                f'<div class="pp-qcard"><span class="pp-qnum">{run["idx"] + 1}</span><div class="pp-qtext">{esc(q["question"])}</div></div></div>', unsafe_allow_html=True)
    for letter in ("A", "B", "C", "D"):
        if letter in q["options"]:
            st.button(f"{letter}.  {q['options'][letter]}", key=f"gopt_{run['uid']}_{run['idx']}_{letter}", on_click=_answer, args=(letter,), use_container_width=True)
    st.button("Quit without saving", key=f"gquit_{run['uid']}", on_click=_quit)


# ------------------------------------------------------------------ result
def _save(student_id: str, run: dict[str, Any], out: dict[str, Any]) -> dict[str, Any] | None:
    before = progress.get_progress(student_id)
    title = games.title_of(run["game"])
    if not games.record_result(student_id, run["game"], run["subject"], out["correct"], out["total"], out["taken"]):
        return run.get("saved")                                           # never counted twice
    db.record_game_round(student_id, run["subject"], out["questions"], out["answers"])   # XP and streak only: game mistakes are not performance
    perfect = bool(out["total"] >= games.MIN_PLAYABLE and out["correct"] == out["total"])
    if perfect:
        db.add_achievement(student_id, "perfect_quiz", "Perfect Quiz")
    after = progress.get_progress(student_id)
    miles = progress.new_milestones(student_id, before, after)
    for code, t in miles:
        db.add_achievement(student_id, code, t)
    return {"xp": progress.xp_for(out["answered"], out["correct"], True, perfect), "streak": after["streak"], "milestones": [t for _, t in miles]}


def _render_result(student_id: str, run: dict[str, Any]) -> None:
    out = games.outcome(run)
    if run["saved"] is None and out["answered"] > 0:
        try:
            run["saved"] = _save(student_id, run, out)
        except Exception as exc:  # noqa: BLE001
            st.error("Prep.AI could not save this result. Your answers are shown below; press Save again to retry.")
            if st.session_state.get("debug_mode"):
                st.exception(exc)
            st.button("Save again", key="game_resave")
    title = games.title_of(run["game"])
    st.markdown(f"#### {title} · {run['subject']}: result")
    if run["game"] == "rapid" and run["exhausted"]:
        st.info("You answered every available question before the 60 seconds ended. Try another subject or Mixed for a bigger pool.")
    c = st.columns(4)
    c[0].metric("Correct", out["correct"])
    c[1].metric("Answered", out["answered"] if run["game"] == "rapid" else f"{out['answered']} of {out['total']}")
    c[2].metric("Accuracy", f"{100 * out['correct'] / out['answered']:.0f}%" if out["answered"] else "–")
    c[3].metric("Time", clock(out["taken"]))
    if out["answered"] == 0:
        st.warning("No question was answered, so nothing was saved.")
    elif run["saved"]:
        s = run["saved"]
        st.success(f"⭐ +{s['xp']} XP · 🔥 {s['streak']}-day streak" + "".join(f"  \n🏅 **{m}**" for m in s["milestones"]) + "  \nResult saved to your game history and the leaderboard. Game answers are not counted in your performance or Mistakes Diary.")
    with st.expander("Review answers"):
        for j, q in enumerate(out["questions"]):
            sel, right = out["answers"].get(j), str(q.get("answer", "")).strip()
            mark = "Skipped" if not sel else "Correct" if sel == right else "Incorrect"
            st.markdown(k.qcard(j + 1, q.get("question", "")), unsafe_allow_html=True)
            st.markdown(k.badge(mark, "ok" if mark == "Correct" else "err" if mark == "Incorrect" else "warn"), unsafe_allow_html=True)
            st.write(f"**Your answer:** {sel or 'Skipped'} · **Correct answer:** {right}")
            st.write(f"**Explanation:** {q.get('explanation', 'No explanation provided.')}")
    a, b = st.columns(2)
    if a.button("Play again", key="game_again", type="primary", use_container_width=True):
        st.session_state.pop(KEY, None)
        st.rerun()
    b.button("Open leaderboard", key="game_to_lb", on_click=go_to, args=("Leaderboard",), use_container_width=True)


# ------------------------------------------------------------------ page
def render_games(student_id: str, new_quiz: Callable[..., dict] | None = None, render_quiz_taker: Callable[[str], None] | None = None,
                 generate: Callable[[str, int], list[dict[str, Any]]] | None = None) -> None:
    hero("Learning Games", "Timed rounds of real MCQs. Every answer counts towards your mastery, streak, XP and the leaderboard.")
    run = st.session_state.get(KEY)
    if run:
        if run["done"]:
            _render_result(student_id, run)
        else:
            _play()
        return

    best = games.best(student_id)
    cols = st.columns(2, gap="medium")
    for col, (key, g) in zip(cols, games.GAMES.items()):
        with col, st.container(border=True, key=f"game_{key}", height=330):
            st.markdown(f'<div class="pp-game"><b class="t">{g["title"]}</b><p>{g["blurb"]}</p></div>', unsafe_allow_html=True)
            b = best.get(key)
            if not b:
                st.caption("You have not finished this game yet.")
            elif key == "rapid":
                st.caption(f"Best: {b['correct']} correct of {b['total']} answered")
            else:
                st.caption(f"Best: {b['correct']}/{b['total']}" + (f" in {clock(b['taken_sec'])}" if b["taken_sec"] is not None else ""))
            subject = st.selectbox("Subject", ["Mixed"] + games.SUBJECTS, key=f"game_subject_{key}")
            n = 0
            if key == "quick":
                lo, hi, dflt = g["counts"]
                n = st.slider("Number of MCQs", lo, hi, dflt, key="game_n_quick")
            if st.button("Play", key=f"game_play_{key}", type="primary", icon=f":material/{g['icon']}:", use_container_width=True):
                _start(student_id, key, subject, int(n), generate)
    with st.container(border=True, key="game_daily"):
        st.markdown('<div class="pp-game"><b class="t">Daily Challenge</b><p>Five questions, the same for every student, once a day, with bonus XP.</p></div>', unsafe_allow_html=True)
        st.button("Open Daily Challenge", key="game_go_daily", on_click=go_to, args=("Daily Challenge",))
    st.markdown("### My recent games")
    h = games.history(student_id, 8)
    if h:
        st.markdown("".join(k.row(f"{games.title_of(x['game'])} · {x['subject']}", (x["created_at"] or "")[:10],
                                  k.badge(f"{x['correct']}/{x['total']}" + (f" · {clock(x['taken_sec'])}" if x["taken_sec"] is not None else ""), "ok" if x["total"] and x["correct"] / x["total"] >= .75 else "warn" if x["total"] and x["correct"] / x["total"] >= .5 else "err")) for x in h), unsafe_allow_html=True)
    else:
        st.markdown(k.empty("No games finished yet. Pick one above."), unsafe_allow_html=True)
    st.markdown("### Leaderboard")
    leaderboard_pages.render_board(student_id, key_prefix="games", top=5)
