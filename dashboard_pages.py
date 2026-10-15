"""The redesigned dashboard: greeting, daily finish line, schedule, score estimate, subject strengths, recent activity, quick-access cards.

Every number comes from stored data (see dashboard_data.py); where there is none an honest empty state with a working action is shown.
"""
from __future__ import annotations

from datetime import datetime
from html import escape as esc
from typing import Callable

import streamlit as st

import dashboard_data as dd
import games
import goals
import leaderboard_pages
import progress
import score_estimate
import ui_kit as k
from adaptive import next_best_action
from db import weak_strong_areas, dashboard_stats, due_revisions
from ui import go_to

# (title, description, page, material icon): only pages that exist in the app
FEATURES = [
    ("Practice Zone", "Quizzes, weak topics, smart revision and flashcards", "Practice", "bolt"),
    ("Personalized Learning", "Study your own PDF or notes with AI", "Learn", "menu_book"),
    ("AI Tutor", "Ask any question and get a step-by-step answer", "AI Tutor", "smart_toy"),
    ("Exam Mode", "Timed exam practice with full results", "Exam", "assignment"),
    ("Mock Test", "A full-length MDCAT-style paper", "Mock Test", "quiz"),
    ("Daily Challenge", "5 questions a day and a leaderboard", "Daily Challenge", "emoji_events"),
    ("Mistakes & Revision", "Fix what you got wrong and revise on time", "Today", "history"),
    ("Study Plan", "A plan from your quizzes, chapters or documents", "Study Plan", "event_note"),
    ("Research Agent", "Web research with sources", "Research Agent", "travel_explore"),
    ("Merit Calculator", "Your aggregate and likely colleges", "Merit Calculator", "calculate"),
    ("Path Finder", "Compare programs and plan your path", "Path Finder", "alt_route"),
    ("My Classes", "Assignments and deadlines from your tutor", "My Classes", "groups"),
]


def _due_text(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d %b, %H:%M")
    except (TypeError, ValueError):
        return ""


def _greeting_line(p: dict) -> str:
    if p["goal_done"]:
        return "Daily goal reached. Anything more today is a bonus."
    if p["streak_at_risk"]:
        return f"Your {p['streak']}-day streak ends tonight. Answer {p['goal'] - p['today_questions']} more question(s) to keep it."
    if p["today_questions"]:
        return f"{p['today_questions']} of {p['goal']} questions done today. Keep going."
    return "Start with one quiz today. Small, steady steps beat last-minute cramming."


def render_greeting(name: str, student: dict, p: dict) -> None:
    left, right = st.columns([3, 2])
    left.markdown(k.greeting(name, _greeting_line(p)), unsafe_allow_html=True)
    chips = []
    g = goals.get_goal(student)
    if g["is_set"] and g["days"]:
        chips.append(f"🎯 {esc(g['exam'])}: {g['days']} day{'s' if g['days'] != 1 else ''} to go")
    chips.append(f"{p['total_xp']} XP · best streak {p['best_streak']} day{'s' if p['best_streak'] != 1 else ''}")
    right.markdown('<div class="pp-chips" style="justify-content:flex-end">' + "".join(f'<span class="pp-chip">{c}</span>' for c in chips) + "</div>", unsafe_allow_html=True)


ROW1_H, ROW2_H, ROW3_H = 430, 480, 360      # one fixed height per row: the cards of a row line up; longer content scrolls inside its card


def render_finish_line(student_id: str, p: dict) -> None:
    today = progress.local_today()
    tasks = dd.finish_line_tasks(student_id, today)
    done, total = dd.task_progress(tasks)
    with st.container(border=True, key="card_line", height=ROW1_H):
        st.markdown(k.finish_line(done, total, "Today's Finish Line", "All done. Great work today!" if done == total else f"{total - done} task(s) left. Start with the first one."), unsafe_allow_html=True)
        for t in tasks:
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.markdown(k.task_row(t["title"], t["detail"], t["done"]), unsafe_allow_html=True)
            if not t["done"]:
                c2.button("Open", key=f"go_{t['key']}", on_click=go_to, args=(t["page"],))


def _toggle_done(student_id: str, day, key: str) -> None:
    dd.set_task_done(student_id, day, key, key not in dd.done_keys(student_id, day))          # a second press undoes it


def render_schedule(student_id: str) -> None:
    """One list, no section headings. Every row starts with the icon of the sidebar tab it belongs to. Study-plan rows end with a Done button (it turns green once pressed);
    tutor assignments and quizzes end with Open, because they are finished by doing them."""
    sch = dd.schedule(student_id)
    today = progress.local_today()
    with st.container(border=True, key="card_schedule", height=ROW1_H):
        st.markdown(k.label("Today's schedule"), unsafe_allow_html=True)
        for n, it in enumerate(sch["items"]):
            c_icon, c_text, c_btn = st.columns([1, 9, 2.6], vertical_alignment="center", gap="small")
            with c_icon, st.container(key=f"sch_ico_{n}"):
                st.markdown(f":material/{it['icon']}:")
            badge = k.badge(_due_text(it["due_at"]), "err" if it["status"] == "overdue" else "warn" if it["status"] == "due_soon" else "") if it["due_at"] else ""
            c_text.markdown(k.sch_text(it["title"], it["detail"], it["done"], badge), unsafe_allow_html=True)
            if it["can_done"]:
                c_btn.button("Done", key=f"{'sch_donex_' if it['done'] else 'sch_done_'}{n}", icon=":material/check:" if it["done"] else None, on_click=_toggle_done, args=(student_id, today, it["key"]),
                             use_container_width=True, help="Press again to undo" if it["done"] else "Mark this session as done")
            else:
                c_btn.button("Open", key=f"sch_open_{n}", on_click=go_to, args=(it["route"],), use_container_width=True)
        if not sch["items"]:
            plan = sch["plan"]
            st.markdown(k.empty("Your study plan has ended." if plan and plan.get("ended") else "Nothing scheduled for today. Create a study plan, or wait for your tutor to assign work."), unsafe_allow_html=True)
            st.button("Create a study plan", key="go_plan", on_click=go_to, args=("Study Plan",))


def render_score(stats: dict, student: dict | None = None) -> None:
    g = goals.get_goal(student or {})
    est = score_estimate.estimate(stats["attempted"], stats["correct"], scale=g["scale"])
    with st.container(border=True, key="card_score", height=ROW2_H):
        st.markdown(k.label("Score estimate"), unsafe_allow_html=True)
        if est["ready"]:
            st.markdown(k.gauge(est["score"], est["scale"], est["low"], est["high"]), unsafe_allow_html=True)
            st.markdown(k.score_vs_target(est["score"], g["score"], est["scale"]), unsafe_allow_html=True)
            st.caption(f"Likely range {est['low']}–{est['high']} · practice-based estimate from {est['answered']} answered questions ({est['accuracy']}% correct). Not an official prediction.")
        else:
            st.markdown(k.gauge(None, est["scale"]), unsafe_allow_html=True)
            st.markdown(k.empty(f"Answer {est['needed']} more question(s) to unlock your estimate ({est['answered']} of {est['min_answers']} so far)."), unsafe_allow_html=True)
        st.button("Open Score Predictor", key="go_predictor", on_click=go_to, args=("Score Predictor",))


def render_games_card(student_id: str) -> None:
    with st.container(border=True, key="card_games_dash", height=ROW3_H):
        st.markdown(k.label("Games & challenges"), unsafe_allow_html=True)
        best = games.best(student_id)
        for key, gm in games.GAMES.items():
            b = best.get(key)
            st.markdown(k.row(gm["title"], gm["short"], k.badge(f"Best {b['correct']}/{b['total']}" if key != "rapid" else f"Best {b['correct']} correct", "ok") if b else k.badge("Not played")), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.button("Play a game", key="dash_go_games", on_click=go_to, args=("Learning Games",))
        c2.button("Daily Challenge", key="dash_go_daily", on_click=go_to, args=("Daily Challenge",))


def render_subjects(student_id: str) -> None:
    perf = dd.subject_performance(student_id)
    areas = weak_strong_areas(student_id, 3)
    with st.container(border=True, key="card_subjects", height=ROW2_H):
        st.markdown(k.label("Strengths & weaknesses"), unsafe_allow_html=True)
        st.markdown('<div class="pp-subjects">' + "".join(k.ring(x["mastery"] if x["has_data"] else None, x["short"]) for x in perf) + "</div>", unsafe_allow_html=True)
        if any(x["has_data"] for x in perf):
            if areas["weak"]:
                st.markdown("**Focus on:** " + " · ".join(f"{x['subject']} → {x['topic']}" for x in areas["weak"]))
            if areas["strong"]:
                st.markdown("**Strong in:** " + " · ".join(f"{x['subject']} → {x['topic']}" for x in areas["strong"]))
            if not areas["weak"] and not areas["strong"]:
                st.caption("Topics are called weak or strong after at least 3 answers each.")
            st.button("Revise weak topics", key="go_weak", on_click=go_to, args=("Practice",))
        else:
            st.markdown(k.empty("Complete a quiz to see your mastery by subject."), unsafe_allow_html=True)
            st.button("Take a quiz", key="go_practice_subjects", on_click=go_to, args=("Practice",))


def render_recent(student_id: str) -> None:
    recent = dd.recent_quizzes(student_id, 4)
    action = next_best_action(student_id)
    with st.container(border=True, key="card_recent", height=ROW2_H):
        st.markdown(k.label("Next step"), unsafe_allow_html=True)
        st.markdown(f"**{action['title']}**  \n{action['reason']}" + (f"  \n*{action['subject']} → {action['topic']}*" if action.get("topic") else ""))
        st.markdown(k.label("Recent quizzes"), unsafe_allow_html=True)
        if recent:
            st.markdown("".join(k.row(f"{r['subject']} · {r['topic']}", r["when"], k.badge(f"{r['score']:.0f}%", "ok" if r["score"] >= 75 else "warn" if r["score"] >= 50 else "err")) for r in recent), unsafe_allow_html=True)
        else:
            st.markdown(k.empty("No quizzes yet."), unsafe_allow_html=True)


def render_features(per_row: int = 4) -> None:
    st.markdown("### What do you want to do?")
    for i in range(0, len(FEATURES), per_row):
        cols = st.columns(per_row, gap="medium")
        for col, (title, desc, page, icon) in zip(cols, FEATURES[i:i + per_row]):
            with col, st.container(border=True, key=f"feat_{page.replace(' ', '_')}_{title.replace(' ', '_')}"):
                st.button(title, key=f"open_{title}", icon=f":material/{icon}:", on_click=go_to, args=(page,), use_container_width=True)
                st.caption(desc)


def render_top(student_id: str, name: str, student: dict) -> dict:
    """All dashboard cards. Returns the stats so the caller can add detail sections below."""
    p = progress.get_progress(student_id)
    stats = dashboard_stats(student_id)
    render_greeting(name, student, p)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        render_finish_line(student_id, p)
    with c2:
        render_schedule(student_id)
    c3, c4, c5 = st.columns(3, gap="medium")
    with c3:
        render_score(stats, student)
    with c4:
        render_subjects(student_id)
    with c5:
        render_recent(student_id)
    c6, c7 = st.columns(2, gap="medium")
    with c6:
        render_games_card(student_id)
    with c7:
        leaderboard_pages.render_card(student_id, ROW3_H)
    render_features()
    return stats
