"""Mistakes Diary page.

Each open mistake has a "Teach me this mistake" button. The lesson opens at the top; when the student moves on (the "Next mistake" button, or by asking
to be taught another mistake) the taught mistake leaves the diary and the count in the sidebar goes down by one.
Removing happens in button callbacks, which run before the page is drawn, so the sidebar badge is already up to date on that rerun.
"""
from __future__ import annotations

from html import escape as esc
from typing import Any, Callable

import streamlit as st

import diary
import ui_kit as k
from ui import hero

PAGE = 10
CUR, TEXT, SHOW = "diary_current", "diary_text", "diary_show"


# ------------------------------------------------------------------ callbacks (run before the next draw)
def _teach(student_id: str, mistake_id: int) -> None:
    prev = st.session_state.get(CUR)
    if prev and prev != mistake_id:
        diary.resolve(student_id, prev)                       # moving on to another mistake: the one just taught is done
        st.session_state.get(TEXT, {}).pop(prev, None)
    st.session_state[CUR] = mistake_id


def _next(student_id: str) -> None:
    cur = st.session_state.pop(CUR, None)
    if cur:
        diary.resolve(student_id, cur)
        st.session_state.get(TEXT, {}).pop(cur, None)


def _more() -> None:
    st.session_state[SHOW] = st.session_state.get(SHOW, PAGE) + PAGE


# ------------------------------------------------------------------ pieces
def _card(m: dict[str, Any], *, taught: bool = False) -> None:
    st.markdown(f'<div class="pp-qcard"><span class="pp-qnum">?</span><div class="pp-qtext">{esc(m["question"])}</div></div>', unsafe_allow_html=True)
    meta = k.badge(m["subject"]) + (" " + k.badge(m["topic"]) if m["topic"] else "") + (" " + k.badge(m["difficulty"]) if m["difficulty"] else "")
    st.markdown(meta, unsafe_allow_html=True)
    st.markdown(f'<div class="pp-mistake"><div class="bad"><small>Your answer</small>{esc(diary.option_text(m, m["wrong"]))}</div>'
                f'<div class="good"><small>Correct answer</small>{esc(diary.option_text(m, m["correct"]))}</div></div>', unsafe_allow_html=True)
    if m["explanation"] and not taught:
        with st.expander("Saved explanation"):
            st.write(m["explanation"])


def _lesson(m: dict[str, Any], student_id: str, orch: Any, create_context: Callable[..., Any], save_tutor_turn: Callable[..., None]) -> str:
    """The lesson text for the mistake being taught (kept in the session so reruns do not call the AI again)."""
    cache = st.session_state.setdefault(TEXT, {})
    if m["id"] in cache:
        return cache[m["id"]]
    with st.spinner("Your tutor is preparing this lesson..."):
        try:
            prompt = diary.teach_prompt(m)
            ctx = create_context(prompt, m["subject"], m["topic"] or m["subject"], "Medium",
                                 f"Question: {m['question']}\nStudent's wrong answer: {diary.option_text(m, m['wrong'])}\nCorrect answer: {diary.option_text(m, m['correct'])}\nSaved explanation: {m['explanation']}")
            text = (orch.tutor_request(ctx) or "").strip()
            if not text:
                raise ValueError("empty lesson")
            try:
                save_tutor_turn(f"Teach me this mistake: {m['question'][:200]}", text, m["subject"], m["topic"])
            except Exception:  # noqa: BLE001 - saving the chat turn must not lose the lesson
                pass
        except Exception:  # noqa: BLE001 - AI down, rate limit: show what the app stored instead
            text = diary.fallback_teaching(m)
    cache[m["id"]] = text
    return text


# ------------------------------------------------------------------ page
def render_diary(student_id: str, orch: Any, create_context: Callable[..., Any], save_tutor_turn: Callable[..., None]) -> None:
    hero("Mistakes Diary", "Every question you got wrong, in one place. Press Teach me this mistake, read the lesson, then move on to the next one: finished mistakes leave the diary.")
    items = diary.open_mistakes(student_id)
    cur_id = st.session_state.get(CUR)
    current = next((m for m in items if m["id"] == cur_id), None)
    if cur_id and not current:
        st.session_state.pop(CUR, None)                         # it was fixed or removed elsewhere

    if not items:
        st.markdown(k.empty("Your Mistakes Diary is empty. Wrong answers from Practice, Exam, Mock Test and quizzes will appear here. (Learning Games are not counted.)"), unsafe_allow_html=True)
        return

    st.metric("Mistakes to review", len(items))
    subjects = sorted({m["subject"] for m in items})
    pick = "All subjects"
    if len(subjects) > 1:
        pick = st.selectbox("Subject", ["All subjects"] + subjects, key="diary_subject")

    if current:
        with st.container(border=True, key="diary_teaching"):
            st.markdown(k.label("Teaching you now"), unsafe_allow_html=True)
            _card(current, taught=True)
            st.markdown(_lesson(current, student_id, orch, create_context, save_tutor_turn))
            left = len(items) - 1
            st.button("Next mistake" if left else "Finish: no more mistakes", key="diary_next", type="primary", icon=":material/arrow_forward:", on_click=_next, args=(student_id,))
            st.caption("This mistake leaves your diary when you move on." + (f" {left} more to go." if left else ""))

    rest = [m for m in items if m["id"] != cur_id and (pick == "All subjects" or m["subject"] == pick)]
    limit = st.session_state.get(SHOW, PAGE)
    for m in rest[:limit]:
        with st.container(border=True, key=f"diary_item_{m['id']}"):
            _card(m)
            st.button("Teach me this mistake", key=f"diary_teach_{m['id']}", icon=":material/school:", on_click=_teach, args=(student_id, m["id"]))
    if len(rest) > limit:
        st.button(f"Show more ({len(rest) - limit} left)", key="diary_more", on_click=_more)
    elif not rest and current:
        st.caption("This is your last mistake.")
