"""Study Plan display: the saved plan as a weekly calendar (days across, hours down), with a day-by-day list and a calendar download.

The plan is always read from the database (the latest saved plan), so it is the same after a page reload or a new login.
Pure layout lives in plan_calendar.py; this file only draws it.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from html import escape as esc

import streamlit as st

import config
import dashboard_data
import plan_calendar as pc


def _local_now() -> datetime:
    return datetime.utcnow() + timedelta(minutes=config.PROGRESS_TZ_OFFSET_MIN)


def render_saved_plan(student_id: str) -> None:
    plan = dashboard_data.latest_plan(student_id)
    if not plan or not plan["days"]:
        st.info("You have no study plan yet. Fill in the form above and press the button to create one.")
        return
    start_t = st.time_input("I start studying at", value=st.session_state.get("plan_start", time(17, 0)), step=1800, key="plan_start",
                            help="Sessions follow each other from this time, with a 10 minute break between them.")
    created = datetime.fromisoformat(plan["created_at"]) + timedelta(minutes=config.PROGRESS_TZ_OFFSET_MIN)
    days = pc.layout(plan["days"], created.date(), start_t.hour * 60 + start_t.minute)
    total_min = sum(d["minutes"] for d in days)
    st.markdown(f"#### Your plan: {esc(str(plan.get('exam_name') or 'Exam'))}" + (f" · exam on {esc(str(plan['exam_date']))}" if plan.get("exam_date") else ""))
    st.caption(f"{len(days)} day(s) · {sum(len(d['events']) for d in days)} sessions · {total_min // 60} h {total_min % 60:02d} min of study in total. "
               "Colours show the kind of session; dashed blocks are still ahead.")
    st.markdown(pc.legend(), unsafe_allow_html=True)
    chunks = pc.weeks(days)
    now = _local_now()
    if len(chunks) == 1:
        st.markdown(pc.to_html(chunks[0], now), unsafe_allow_html=True)
    else:
        tabs = st.tabs([f"Week {i + 1}" for i in range(len(chunks))])
        for tab, chunk in zip(tabs, chunks):
            with tab:
                st.markdown(pc.to_html(chunk, now), unsafe_allow_html=True)
    with st.expander("Day-by-day list"):
        for d in days:
            st.markdown(f"**{esc(pc.day_summary(d))}**")
            for e in d["events"]:
                st.markdown(f"- `{pc.hhmm(e['start'])}-{pc.hhmm(e['end'])}` {esc(e['subject'])}: {esc(e['topic'])} ({e['minutes']} min, {esc(e['activity'] or e['kind'])})"
                            + (f"  \n  📖 *{esc(e['source'])}*" if e["source"] else ""))
    st.download_button("Add to my calendar (.ics)", data=pc.to_ics(days), file_name="prep_ai_study_plan.ics", mime="text/calendar", icon=":material/event:", key="plan_ics")
