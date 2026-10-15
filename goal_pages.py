"""The 'Edit goal' dialog (target exam, university, target score, maximum score, exam date)."""
from __future__ import annotations

from datetime import date

import streamlit as st

import goals
import progress

_KEYS = ("goal_exam", "goal_exam_custom", "goal_uni", "goal_score", "goal_scale", "goal_date")


def request_open() -> None:
    """Button callback: ask for the dialog on the next run (the flag is consumed when it opens, so closing it never re-opens it)."""
    st.session_state["_goal_dialog"] = True


def _on_exam_change() -> None:
    exam = st.session_state.get("goal_exam", "Other")
    st.session_state["goal_scale"] = goals.default_scale(exam)    # the maximum follows the exam; the student can still change it


def _body(student_id: str, student: dict) -> None:
    g = goals.get_goal(student)
    today = progress.local_today()
    st.session_state.setdefault("goal_exam", g["exam"] if g["exam"] in goals.EXAMS else ("Other" if g["exam"] else "MDCAT"))
    st.session_state.setdefault("goal_exam_custom", g["exam"] if g["exam"] and g["exam"] not in goals.EXAMS else "")
    st.session_state.setdefault("goal_uni", g["university"])
    st.session_state.setdefault("goal_scale", g["scale"])
    st.session_state.setdefault("goal_score", g["score"] or 0)
    st.session_state.setdefault("goal_date", date.fromisoformat(g["date"]) if g["date"] and g["date"] >= today.isoformat() else today)
    exam_choice = st.selectbox("Target exam", goals.EXAMS, key="goal_exam", on_change=_on_exam_change)
    exam = st.text_input("Exam name", key="goal_exam_custom", placeholder="e.g. AKU Test") if exam_choice == "Other" else exam_choice
    uni = st.text_input("Target university / college (optional)", key="goal_uni", placeholder="e.g. King Edward Medical University")
    c1, c2 = st.columns(2)
    scale = c1.number_input("Maximum score", min_value=1, max_value=1000, step=1, key="goal_scale", help="The marks the exam is out of. Changes the scale of your score estimate.")
    score = c2.number_input("Desired score (0 = none)", min_value=0, max_value=1000, step=1, key="goal_score")
    when = st.date_input("Exam date", min_value=today, key="goal_date")
    a, b = st.columns(2)
    if a.button("Save goal", type="primary", key="goal_save", use_container_width=True):
        clean, errors = goals.validate(exam, uni, score, scale, when, today)
        if errors:
            for e in errors:
                st.error(e)
            return
        goals.save_goal(student_id, clean)
        for key in _KEYS:
            st.session_state.pop(key, None)
        st.session_state["_goal_saved"] = True
        st.rerun()
    if b.button("Cancel", key="goal_cancel", use_container_width=True):
        for key in _KEYS:
            st.session_state.pop(key, None)
        st.rerun()


def open_if_requested(student_id: str, student: dict) -> None:
    """Call once per run near the top of the page. Opens the dialog when the Edit goal button was pressed."""
    if st.session_state.get("_goal_saved"):
        st.session_state.pop("_goal_saved", None)
        st.toast("Goal saved.")
    if not st.session_state.pop("_goal_dialog", False):
        return
    for key in _KEYS:
        st.session_state.pop(key, None)
    dialog = getattr(st, "dialog", None)
    if dialog:
        dialog("Edit your goal", width="small")(_body)(student_id, student)
    else:                                          # very old Streamlit: show the same form in the page
        with st.container(border=True):
            st.subheader("Edit your goal")
            _body(student_id, student)
