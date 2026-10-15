"""Leaderboard widgets: the full page and a compact card for the dashboard."""
from __future__ import annotations

import streamlit as st

import leaderboard
import ui_kit as k
from ui import go_to, hero

HOW = ("**How points work.** Points are the XP you earn from real activity: 2 per answered question, 3 per correct answer, 10 per finished quiz, 20 for a perfect quiz "
       "and the Daily Challenge bonus. Practice, exams, mock tests, games and the Daily Challenge all count once. Ties go to more correct answers, then the earlier sign-up. "
       "Names are shortened (first name and last initial); emails and phone numbers are never shown.")


def render_board(student_id: str, key_prefix: str = "lb", top: int = 10) -> None:
    period = st.radio("Period", list(leaderboard.PERIODS), format_func=leaderboard.PERIODS.get, horizontal=True, key=f"{key_prefix}_period", label_visibility="collapsed")
    v = leaderboard.view(student_id, period, top)
    if not v["rows"]:
        st.markdown(k.empty("Nobody has earned points " + ("this week" if period == "week" else "yet") + ". Finish a quiz or a game to appear here."), unsafe_allow_html=True)
        st.button("Play a game", key=f"{key_prefix}_go_games", on_click=go_to, args=("Learning Games",))
    else:
        st.markdown(k.leaderboard_rows(v["rows"], v["me"]), unsafe_allow_html=True)
        if v["count"] == 1:
            st.caption("You are the only student with points so far. The board fills as more students practise on this app.")
        elif v["me"]:
            st.caption(f"You are #{v['me']['rank']} of {v['count']}.")
        else:
            st.caption("You have no points in this period yet. Finish a quiz to join the board.")
    with st.expander("How points are counted"):
        st.markdown(HOW)


def render_leaderboard_page(student_id: str) -> None:
    hero("Leaderboard", "Ranked by the XP students have earned from real practice. No made-up scores.")
    with st.container(border=True, key="card_leaderboard"):
        render_board(student_id)


def render_card(student_id: str, height: int | None = None) -> None:
    """Compact top-5 card for the dashboard."""
    with st.container(border=True, key="card_lb_dash", **({"height": height} if height else {})):
        st.markdown(k.label("Leaderboard · this week"), unsafe_allow_html=True)
        v = leaderboard.view(student_id, "week", 5)
        if v["rows"]:
            st.markdown(k.leaderboard_rows(v["rows"], v["me"]), unsafe_allow_html=True)
        else:
            st.markdown(k.empty("No points this week yet."), unsafe_allow_html=True)
        st.button("Full leaderboard", key="dash_go_lb", on_click=go_to, args=("Leaderboard",))
