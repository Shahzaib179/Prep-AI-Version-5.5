"""Score Predictor page: the practice-based estimate (score_estimate.py), your target, the trend, accuracy by subject, advice and the leaderboard.

The estimate is the same one the dashboard shows. It is not an official exam prediction, and nothing here is invented: with too little data the page says so.
"""
from __future__ import annotations

import streamlit as st

import dashboard_data as dd
import goals
import leaderboard_pages
import progress
import score_estimate
import ui_kit as k
from db import dashboard_stats, due_revisions, weak_topics
from db_core import connect
from ui import go_to, hero


def estimate_for(student_id: str, student: dict) -> tuple[dict, dict, dict]:
    """(estimate, goal, stats) on the student's own marks scale."""
    goal = goals.get_goal(student)
    stats = dashboard_stats(student_id)
    return score_estimate.estimate(stats["attempted"], stats["correct"], scale=goal["scale"]), goal, stats


def _daily_rows(student_id: str) -> list[tuple[str, int, int]]:
    with connect() as con:
        return [(r[0], int(r[1] or 0), int(r[2] or 0)) for r in con.execute("SELECT day, questions, correct FROM daily_activity WHERE student_id=? AND questions>0 ORDER BY day", (student_id,)).fetchall()]


def render_panel(student_id: str, student: dict) -> None:
    est, goal, stats = estimate_for(student_id, student)
    scale = goal["scale"]
    if est["ready"]:
        st.markdown(k.gauge(est["score"], scale, est["low"], est["high"]), unsafe_allow_html=True)
        st.markdown(k.score_vs_target(est["score"], goal["score"], scale), unsafe_allow_html=True)
        st.caption(f"Likely range {est['low']}–{est['high']} out of {scale} · from {est['answered']} answered questions ({est['accuracy']}% correct). "
                   "This is a practice-based estimate, not an official prediction.")
    else:
        st.markdown(k.gauge(None, scale), unsafe_allow_html=True)
        st.markdown(k.score_vs_target(None, goal["score"], scale), unsafe_allow_html=True)
        st.markdown(k.empty(f"Answer {est['needed']} more question(s) to unlock your estimate ({est['answered']} of {est['min_answers']} so far)."), unsafe_allow_html=True)
        st.button("Start practising", key="pred_go_practice", on_click=go_to, args=("Practice",))


def render_predictor(student_id: str, student: dict) -> None:
    hero("Score Predictor", "An honest estimate from the questions you have answered, shown against your own target.")
    est, goal, stats = estimate_for(student_id, student)
    tab_est, tab_lb = st.tabs(["My estimate", "Leaderboard"])
    with tab_est:
        left, right = st.columns([2, 3], gap="medium")
        with left, st.container(border=True, key="card_pred_gauge"):
            st.markdown(k.label("Your predicted score"), unsafe_allow_html=True)
            render_panel(student_id, student)
            if not goal["is_set"] or not goal["score"]:
                st.caption("Set your target exam and score to see the gap.")
            st.button("Edit goal", key="pred_edit_goal", on_click=lambda: st.session_state.__setitem__("_goal_dialog", True))
        with right:
            with st.container(border=True, key="card_pred_trend"):
                st.markdown(k.label("Trend"), unsafe_allow_html=True)
                pts = score_estimate.trend(_daily_rows(student_id), goal["scale"])
                if len(pts) >= 2:
                    st.markdown(k.trend_svg(pts[-14:], goal["scale"], goal["score"]), unsafe_allow_html=True)
                    st.caption("Running estimate after each practice day (last 14 days with an estimate).")
                else:
                    st.markdown(k.empty("The trend needs your estimate on at least two different practice days."), unsafe_allow_html=True)
            with st.container(border=True, key="card_pred_subjects"):
                st.markdown(k.label("Accuracy by subject"), unsafe_allow_html=True)
                perf = [x for x in dd.subject_performance(student_id)]
                if any(x["has_data"] for x in perf):
                    st.markdown("".join(k.bar_row(x["subject"], f"{x['accuracy']:.0f}% · {x['attempts']} answers" if x["has_data"] else "no data yet", x["accuracy"] if x["has_data"] else None,
                                                  f"Strongest: {x['strongest']}" if x.get("strongest") else "") for x in perf), unsafe_allow_html=True)
                else:
                    st.markdown(k.empty("Complete a quiz to see your accuracy by subject."), unsafe_allow_html=True)
            with st.container(border=True, key="card_pred_tips"):
                st.markdown(k.label("How to improve"), unsafe_allow_html=True)
                p = progress.get_progress(student_id)
                tips = score_estimate.recommendations(est, goal["score"], weak_topics(student_id, 2), len(due_revisions(student_id)), p["today_questions"], p["goal"])
                st.markdown("\n".join(f"- {t}" for t in tips) if tips else k.empty("Nothing to suggest yet."), unsafe_allow_html=not tips)
                st.button("Practise now", key="pred_go_practice2", on_click=go_to, args=("Practice",))
    with tab_lb:
        leaderboard_pages.render_board(student_id, key_prefix="pred")
