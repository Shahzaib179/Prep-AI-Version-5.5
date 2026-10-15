"""Career Path Finder: the step-by-step profile wizard and the closing recommendation card.

Each step is one form with Back / Save and continue. Answers live in one dict in the session and are saved to the database after every step, so a student
can close the app and continue later. The fields of every step are plain data (STEPS), so the page code is one small renderer.
"""
from __future__ import annotations

from html import escape as esc
from typing import Any

import streamlit as st

import career_profile as cp
import pathfinder_service as pf
import ui_kit as k

PROVINCES = ["Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan", "Islamabad (ICT)", "Azad Kashmir", "Gilgit-Baltistan", "Other"]
SUBJECTS = ["Biology", "Chemistry", "Physics", "Mathematics", "Computer Science", "English", "Urdu", "Pakistan Studies / Islamiat", "Accounting / Economics"]
TESTS = ["MDCAT", "ECAT", "NUST NET", "NUMS", "FAST NU", "GIKI", "SAT", "Other", "None yet"]
YNM = ["Yes", "Somewhat", "No"]
YN = ["Yes", "No", "Not sure"]
ACTIVITIES = ["Solving problems", "Helping people", "Designing or creating", "Experiments and research", "Leading or managing", "Writing and communicating", "Working with computers", "Working with numbers"]
STRENGTHS = ["Mathematics", "Biology", "Physics", "Chemistry", "Computers", "Communication", "Languages", "Drawing / design"]

# field kinds: select, multi, text, area, num, radio, slider. "key" is where the answer is kept in the profile dict.
STEPS: list[dict[str, Any]] = [
    {"id": "A", "title": "Academic background", "blurb": "Where you are now and what you have studied.", "fields": [
        {"key": "level", "kind": "select", "label": "Where are you now?", "options": pf.LEVELS},
        {"key": "stream", "kind": "select", "label": "Which intermediate stream did you complete (or are you in)?", "options": pf.STREAMS},
        {"key": "matric_pct", "kind": "num", "label": "Matric / O-Level %", "help": "0 = not available"},
        {"key": "fsc_pct", "kind": "num", "label": "FSc / A-Level % (so far)", "help": "0 = not available"},
        {"key": "strong_subjects", "kind": "multi", "label": "Your strongest subjects", "options": SUBJECTS},
        {"key": "weak_subjects", "kind": "multi", "label": "Your weakest subjects", "options": SUBJECTS},
        {"key": "entrance_tests", "kind": "multi", "label": "Entrance tests you have taken or plan to take", "options": TESTS},
        {"key": "test_pct", "kind": "num", "label": "Best entry-test % so far (if any)", "help": "0 = not available"},
        {"key": "prepare_test", "kind": "radio", "label": "Are you willing to prepare for an entrance test?", "options": YN},
        {"key": "knows_eligibility", "kind": "radio", "label": "Do you know the minimum eligibility criteria for your target programs?", "options": YN},
        {"key": "applying", "kind": "radio", "label": "When are you applying?", "options": ["This year", "Next year", "Later"]}]},
    {"id": "B", "title": "Interests and preferred degree", "blurb": "What you enjoy and which degrees you are considering.", "fields": [
        {"key": "interests", "kind": "multi", "label": "Which areas interest you most?", "options": "INTEREST_MAP"},
        {"key": "activities", "kind": "multi", "label": "What activities do you like?", "options": ACTIVITIES},
        {"key": "degree1", "kind": "text", "label": "Degree you are considering (1)", "placeholder": "e.g. MBBS"},
        {"key": "degree2", "kind": "text", "label": "Degree you are considering (2)", "placeholder": "e.g. Pharm-D"},
        {"key": "degree3", "kind": "text", "label": "Degree you are considering (3)", "placeholder": "e.g. BS Computer Science"},
        {"key": "why_degrees", "kind": "area", "label": "Why do you want to study each of these?"},
        {"key": "knows_subjects", "kind": "radio", "label": "Do you understand the main subjects taught in these degrees?", "options": YNM},
        {"key": "influence", "kind": "radio", "label": "Is the choice your own, or influenced by family or friends?", "options": ["My own choice", "Mostly family", "Mostly friends", "A mix"]}]},
    {"id": "C", "title": "Skills, aptitude and personality", "blurb": "How you like to work and what you are good at.", "fields": [
        {"key": "strengths", "kind": "multi", "label": "Where are you strongest?", "options": STRENGTHS},
        {"key": "style", "kind": "radio", "label": "Do you prefer practical work, theory, research or working with people?", "options": ["Practical work", "Theory", "Research", "Working with people", "A mix"]},
        {"key": "analytical", "kind": "slider", "label": "How comfortable are you with analytical problems? (1 low, 5 high)"},
        {"key": "teamwork", "kind": "slider", "label": "How much do you enjoy teamwork and leadership? (1 low, 5 high)"},
        {"key": "improve", "kind": "radio", "label": "Are you willing to improve your weaker areas?", "options": YNM},
        {"key": "other_skills", "kind": "area", "label": "Your strongest skills outside academics"}]},
    {"id": "D", "title": "Career goals and future", "blurb": "The work you picture yourself doing.", "fields": [
        {"key": "career_aim", "kind": "area", "label": "What kind of professional do you want to become in 5 to 10 years?"},
        {"key": "sector", "kind": "multi", "label": "Where would you like to work?", "options": ["Government", "Private sector", "Freelancing", "Research", "Entrepreneurship"]},
        {"key": "priority", "kind": "radio", "label": "What matters most to you?", "options": ["Income", "Job security", "My interest", "Social impact"]},
        {"key": "location", "kind": "radio", "label": "Do you want to work in Pakistan or abroad?", "options": ["Pakistan", "Abroad", "Open to both"]},
        {"key": "further_study", "kind": "radio", "label": "Do you plan a master's or a professional certification?", "options": ["Master's", "Professional certification", "Both", "Not planning"]},
        {"key": "researched_demand", "kind": "radio", "label": "Have you researched the demand for your field?", "options": YN}]},
    {"id": "E", "title": "University and affordability", "blurb": "Where you could study and what it costs. Fees are not guessed: you give your own budget.", "fields": [
        {"key": "universities", "kind": "area", "label": "Universities you are considering (one per line, up to 5)"},
        {"key": "province", "kind": "select", "label": "Province / domicile", "options": PROVINCES},
        {"key": "annual_budget", "kind": "num", "label": "Yearly fee budget (PKR)", "step": 10000, "max": 5_000_000, "help": "0 = no limit given"},
        {"key": "family_income", "kind": "num", "label": "Family monthly income (PKR), optional", "step": 5000, "max": 5_000_000, "help": "0 = prefer not to say. Used only for scholarship checks and never saved."},
        {"key": "family_support", "kind": "radio", "label": "Can your family support the full program?", "options": ["Yes", "Partly", "No"]},
        {"key": "aid", "kind": "radio", "label": "Would you consider scholarships or financial aid?", "options": ["Yes, I need it", "Maybe", "No"]},
        {"key": "other_city", "kind": "radio", "label": "Are you willing to study in another city?", "options": YN},
        {"key": "checked_accreditation", "kind": "radio", "label": "Have you checked accreditation, faculty and internships?", "options": YN}]},
    {"id": "F", "title": "Commitment and readiness", "blurb": "How ready you are for the years ahead.", "fields": [
        {"key": "ready_years", "kind": "radio", "label": "Are you ready to study consistently for 4+ years?", "options": YNM},
        {"key": "internships", "kind": "radio", "label": "Are you willing to do internships and projects?", "options": YNM},
        {"key": "independent", "kind": "radio", "label": "Can you manage your time independently at university?", "options": YNM},
        {"key": "learn_skills", "kind": "radio", "label": "Are you comfortable learning new professional and technical skills?", "options": YNM},
        {"key": "backup", "kind": "area", "label": "What will you do if you do not get admission to your first choice?"},
        {"key": "concern", "kind": "area", "label": "What is your biggest concern?"}]},
]
STEP_TITLES = [s["title"] for s in STEPS] + ["Questions for your stream", "Compare your top options", "Review and find my path"]
N_STEPS = len(STEP_TITLES)
STREAM_STEP, COMPARE_STEP, REVIEW_STEP = len(STEPS), len(STEPS) + 1, len(STEPS) + 2


# ------------------------------------------------------------------ one field
def _field(spec: dict[str, Any], data: dict[str, Any], step: int, interest_map: list[str]) -> Any:
    key, kind, label = f"cp{step}_{spec['key']}", spec["kind"], spec["label"]
    options = interest_map if spec.get("options") == "INTEREST_MAP" else spec.get("options") or []
    v = data.get(spec["key"])
    if kind == "select":
        return st.selectbox(label, options, index=options.index(v) if v in options else 0, key=key)
    if kind == "multi":
        return st.multiselect(label, options, default=[x for x in (v or []) if x in options], key=key)
    if kind == "radio":
        return st.radio(label, options, index=options.index(v) if v in options else None, key=key, horizontal=len(options) <= 4)
    if kind == "slider":
        return st.slider(label, 1, 5, int(v) if isinstance(v, (int, float)) and 1 <= int(v) <= 5 else 3, key=key)
    if kind == "num":
        return st.number_input(label, 0.0, float(spec.get("max", 100.0)), float(v or 0.0), float(spec.get("step", 0.1)), key=key, help=spec.get("help"))
    if kind == "area":
        return st.text_area(label, value=str(v or ""), key=key, height=90)
    return st.text_input(label, value=str(v or ""), key=key, placeholder=spec.get("placeholder", ""))


def _buttons(step: int, last: bool = False) -> tuple[bool, bool, bool]:
    """(back, next, run) pressed. Back and Next both save what was typed."""
    cols = st.columns([1, 1, 3])
    back = cols[0].form_submit_button("Back", disabled=step == 0, icon=":material/arrow_back:")
    nxt = False if last else cols[1].form_submit_button("Save and continue", type="primary", icon=":material/arrow_forward:")
    run = cols[1].form_submit_button("Find my path", type="primary", icon=":material/alt_route:") if last else False
    return back, nxt, run


def _go(student_id: str, data: dict[str, Any], step: int, delta: int) -> None:
    new = max(0, min(N_STEPS - 1, step + delta))
    st.session_state.cp_data, st.session_state.cp_step = data, new
    try:
        cp.save(student_id, data, new)
    except Exception:  # noqa: BLE001 - saving is a convenience; the wizard must keep working without it
        pass
    st.rerun()


# ------------------------------------------------------------------ the steps
def _step_fields(student_id: str, data: dict[str, Any], step: int, kb: dict[str, Any]) -> None:
    spec = STEPS[step]
    st.markdown(k.label(f"Section {spec['id']}"), unsafe_allow_html=True)
    st.caption(spec["blurb"])
    with st.form(f"cp_form_{step}"):
        new = dict(data)
        for f in spec["fields"]:
            new[f["key"]] = _field(f, data, step, list(kb["interest_map"]))
        back, nxt, _ = _buttons(step)
    if back or nxt:
        _go(student_id, new, step, -1 if back else 1)


def _step_stream(student_id: str, data: dict[str, Any], step: int) -> None:
    stream = data.get("stream") or ""
    st.caption(f"Questions for your stream: **{stream or 'not chosen yet (go back to step 1)'}**. Answer honestly; they only help you reflect.")
    qs = cp.stream_questions(stream)
    saved = dict(data.get("stream_answers") or {})
    with st.form("cp_form_stream"):
        picked = {q: st.radio(q, cp.ANSWERS, index=cp.ANSWERS.index(saved[q]) if saved.get(q) in cp.ANSWERS else None, key=f"cp{step}_s{i}", horizontal=True) for i, q in enumerate(qs)}
        back, nxt, _ = _buttons(step)
    if back or nxt:
        _go(student_id, {**data, "stream_answers": {q: a for q, a in picked.items() if a}}, step, -1 if back else 1)


def _step_compare(student_id: str, data: dict[str, Any], step: int) -> None:
    st.caption("Give each of your top options a score from 1 (weak) to 5 (strong) on every criterion. Prep.AI multiplies each score by the weight and adds them up.")
    prev = {o.get("name", ""): o.get("scores", {}) for o in (data.get("options") or [])}
    names = [str(data.get(f"degree{i}") or "").strip() for i in (1, 2, 3)]
    with st.form("cp_form_compare"):
        w = st.columns(len(cp.CRITERIA))
        for c, (_, label, weight) in zip(w, cp.CRITERIA):
            c.caption(f"{label}: {weight}%")
        options = []
        for i in range(cp.MAX_OPTIONS):
            name = st.text_input(f"Option {i + 1}", value=names[i] if i < len(names) else "", key=f"cp{step}_n{i}", placeholder="Degree and university, e.g. BS CS at FAST")
            cols = st.columns(len(cp.CRITERIA))
            scores = {}
            for c, (ck, label, _) in zip(cols, cp.CRITERIA):
                scores[ck] = c.slider(label, 1, 5, int((prev.get(name) or {}).get(ck, 3)), key=f"cp{step}_{i}_{ck}", label_visibility="collapsed", help=label)
            options.append({"name": name.strip(), "scores": scores})
        st.info(cp.DISCLAIMER)
        back, nxt, _ = _buttons(step)
    if back or nxt:
        _go(student_id, {**data, "options": options}, step, -1 if back else 1)


def _ranking_html(ranked: list[dict[str, Any]]) -> str:
    rows = "".join(f'<div class="pp-barrow"><div class="top"><span>{esc(r["name"])}</span><span>{r["percent"]:.0f}%</span></div><div class="pp-bar{" ok" if i == 0 else ""}"><i style="width:{r["percent"]:.0f}%"></i></div></div>'
                   for i, r in enumerate(ranked))
    return rows or k.empty("No option has a name yet. Go back to step 8 and name at least one option.")


def _step_review(student_id: str, data: dict[str, Any], step: int, pre: dict[str, Any]) -> dict[str, Any] | None:
    st.caption("Check your profile, tick the admission checklist, then press Find my path.")
    gaps = cp.missing_for_run(data)
    if gaps:
        st.warning("Path Finder works better with: " + "; ".join(gaps) + ".")
    ranked = cp.rank_options(data.get("options") or [])
    st.markdown("##### Your weighted comparison")
    st.markdown(_ranking_html(ranked), unsafe_allow_html=True)
    ticks = list(data.get("checklist") or [])
    with st.form("cp_form_review"):
        st.markdown("##### Final admission checklist")
        new_ticks = [c for i, c in enumerate(cp.CHECKLIST) if st.checkbox(c, value=c in ticks, key=f"cp{step}_c{i}")]
        st.markdown("##### How Path Finder should work")
        c1, c2, c3 = st.columns(3)
        use_web = c1.checkbox("Search trusted websites", True, key="cp_web")
        use_docs = c2.checkbox("Use my uploaded documents", True, key="cp_docs")
        use_signals = c3.checkbox("Use my Prep.AI strengths", True, key="cp_sig")
        back, _, run = _buttons(step, last=True)
    new = {**data, "checklist": new_ticks}
    if back:
        _go(student_id, new, step, -1)
    if run:
        st.session_state.cp_data = new
        try:
            cp.save(student_id, new, step)
        except Exception:  # noqa: BLE001
            pass
        return {"profile": cp.to_pf_profile(new), "data": new, "use_web": use_web, "use_docs": use_docs, "use_signals": use_signals}
    return None


# ------------------------------------------------------------------ public
def render_wizard(student_id: str, kb: dict[str, Any], pre: dict[str, Any]) -> dict[str, Any] | None:
    """Draws the current step. Returns the run request (profile and switches) when the student presses Find my path, otherwise None."""
    if "cp_data" not in st.session_state:
        data, step = cp.load(student_id)
        for key in ("matric_pct", "fsc_pct", "test_pct"):                      # marks from the Merit Calculator, only where the student has not typed any
            if not data.get(key) and pre.get(key):
                data[key] = pre[key]
        st.session_state.cp_data, st.session_state.cp_step = data, min(step, N_STEPS - 1)
    data, step = st.session_state.cp_data, int(st.session_state.get("cp_step", 0))
    done = round(100 * step / (N_STEPS - 1))
    st.markdown(f'<div class="pp-barrow"><div class="top"><span>Step {step + 1} of {N_STEPS}: {esc(STEP_TITLES[step])}</span><span>{done}% done</span></div>'
                f'<div class="pp-bar"><i style="width:{done}%"></i></div></div>', unsafe_allow_html=True)
    if step < len(STEPS):
        _step_fields(student_id, data, step, kb)
    elif step == STREAM_STEP:
        _step_stream(student_id, data, step)
    elif step == COMPARE_STEP:
        _step_compare(student_id, data, step)
    else:
        return _step_review(student_id, data, step, pre)
    return None


def start_over(student_id: str) -> None:
    for key in ("cp_data", "cp_step", "pf_state"):
        st.session_state.pop(key, None)
    try:
        cp.clear(student_id)
    except Exception:  # noqa: BLE001
        pass


def render_recommendation(data: dict[str, Any], programs: list[dict[str, Any]]) -> None:
    """My Recommendation: 3 degree options, the universities to shortlist, 1 backup plan."""
    rec = cp.recommendation(data, programs)
    st.markdown("#### My recommendation")
    c = st.columns(3)
    with c[0]:
        st.markdown(k.label("3 degree options"), unsafe_allow_html=True)
        for d in rec["degrees"] or []:
            st.markdown(f"**{esc(d['name'])}**  \n<small>{esc(d['note'])}</small>", unsafe_allow_html=True)
        if not rec["degrees"]:
            st.caption("Name your options in step 8, or choose an interest, to see degrees here.")
    with c[1]:
        st.markdown(k.label("Universities to shortlist"), unsafe_allow_html=True)
        for u in rec["universities"]:
            st.markdown(f"- {esc(u)}")
        st.caption("These are the ones you entered. Check merit, fees and accreditation on each official site (see the Programs and Accreditation tabs)." if rec["universities"]
                   else "You have not listed universities yet (step 5). Prep.AI does not guess them: shortlist 3 to 5 from the official lists.")
    with c[2]:
        st.markdown(k.label("1 backup plan"), unsafe_allow_html=True)
        st.write(rec["backup"] or "You have not written a backup plan yet (step 6). Choose one in case your first choice does not work out.")
    st.caption(cp.DISCLAIMER)
