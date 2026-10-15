"""Static preview of the redesigned dashboard (no Streamlit needed).

Runs the REAL dashboard code (dashboard_pages.render_top, ui_kit, theme CSS, navigation) against a small seeded database with a stand-in
for the few Streamlit calls it uses, writes HTML shaped like Streamlit's DOM, and screenshots it with headless Chromium at desktop and phone widths.
It checks our own HTML/CSS. It does not prove how Streamlit itself lays the page out; use `streamlit run app.py` for that.

    python scripts/preview_ui.py OUT_DIR
"""
from __future__ import annotations

import html as H
import pathlib
import sys
import tempfile
import types
from datetime import datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT: list = []
class _State(dict):
    def __getattr__(self, k):
        try: return self[k]
        except KeyError: raise AttributeError(k)
    def __setattr__(self, k, v): self[k] = v
STATE: dict = _State()
TARGET: list[list] = [OUT]          # emitters write into the innermost target (a column or container buffer)


def _emit(x) -> None:
    TARGET[-1].append(x)


def _html(items) -> str:
    return "".join(i if isinstance(i, str) else i.html() for i in items)


class _Box:
    """A container or column: its own buffer, wrapped in open/close markup. Used as a context manager and (for columns) directly: col.markdown(...)."""
    def __init__(self, o="", c=""):
        self.o, self.c, self.buf = o, c, []
    def html(self) -> str:
        return self.o + _html(self.buf) + self.c
    def __enter__(self):
        TARGET.append(self.buf); return self
    def __exit__(self, *a):
        TARGET.pop(); return False
    def __getattr__(self, n):
        fn = getattr(St, n)
        def call(*a, **k):
            TARGET.append(self.buf)
            try: return fn(*a, **k)
            finally: TARGET.pop()
        return call


def _tabs(labels):
    boxes = [_Box(f'<div class="tab"><div class="pp-label">Tab: {H.escape(l)}</div>', "</div>") for l in labels]
    for b in boxes: _emit(b)
    return boxes


class St(types.ModuleType):
    session_state = STATE
    secrets: dict = {}
    @staticmethod
    def markdown(t, unsafe_allow_html=False, **k):
        import re
        m_ = re.fullmatch(r":material/(\w+):", t.strip())
        if m_: _emit(f'<span class="ic" data-icon="{m_.group(1)}">{m_.group(1)[:1].upper()}</span>'); return
        if unsafe_allow_html: _emit(t); return
        t = H.escape(t); t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t); t = re.sub(r"\*(.+?)\*", r"<i>\1</i>", t)
        _emit(f"<h3>{t[4:]}</h3>" if t.startswith("### ") else f'<div data-testid="stMarkdownContainer"><p>{t.replace("  " + chr(10), "<br>")}</p></div>')
    write = markdown
    @staticmethod
    def caption(t, **k): _emit(f'<div data-testid="stCaptionContainer">{H.escape(str(t))}</div>')
    @staticmethod
    def container(border=False, key=None, height=None, **k):
        cls = f' class="st-key-{key}"' if key else ""
        sty = f' style="height:{height}px;overflow:auto;box-sizing:border-box"' if height else ""
        box = _Box(f'<div data-testid="stVerticalBlockBorderWrapper"{cls}{sty}><div data-testid="stVerticalBlock">', "</div></div>") if border else _Box(f"<div{cls}>", "</div>")
        _emit(box); return box
    @staticmethod
    def columns(spec, gap="small", **k):
        n = spec if isinstance(spec, int) else len(spec); w = [1] * n if isinstance(spec, int) else spec
        cols = [_Box(f'<div class="col" style="flex:{x}">', "</div>") for x in w]
        _emit(_Box('<div class="cols">', "</div>")); TARGET[-1][-1].buf.extend(cols)
        return cols
    @staticmethod
    def button(label, key=None, icon=None, on_click=None, args=(), use_container_width=False, type="secondary", **k):
        ic = f'<span class="ic">{H.escape((icon or "").strip(":").split("/")[-1][:1].upper())}</span> ' if icon else ""
        cls = f' class="st-key-{key}"' if key else ""
        _emit(f'<div{cls}><button data-testid="stBaseButton-{type}" kind="{type}">{ic}<p>{H.escape(label)}</p></button></div>'); return False
    @staticmethod
    def checkbox(label, value=False, key=None, **k):
        _emit(f'<label class="cb"><span class="pp-tick {"on" if value else ""}">{"✓" if value else ""}</span> {H.escape(label)}</label>'); return value
    @staticmethod
    def divider(): _emit("<hr>")
    @staticmethod
    def tabs(labels, **k):
        return [_Box(f'<div class="tab"><div class="pp-label">{H.escape(l)}</div>', "</div>") for l in labels] if False else _tabs(labels)
    @staticmethod
    def slider(label, lo=0, hi=100, value=None, **k):
        _emit(f'<div class="pp-label">{H.escape(label)}</div><div class="sel">{value}</div>'); return value
    @staticmethod
    def fragment(*a, **k):
        return a[0] if a and callable(a[0]) else (lambda f: f)
    @staticmethod
    def radio(label, options, index=0, **k): return list(options)[index or 0]
    @staticmethod
    def selectbox(label, options, index=0, **k):
        _emit(f'<div class="pp-label">{H.escape(label)}</div><div class="sel">{H.escape(str(list(options)[index or 0]))}</div>'); return list(options)[index or 0]
    @staticmethod
    def expander(label, **k):
        b = _Box(f'<details><summary>{H.escape(label)}</summary>', "</details>"); _emit(b); return b
    @staticmethod
    def time_input(label, value=None, **k):
        import datetime as _d
        _emit(f'<div class="pp-label">{H.escape(label)}</div><div class="sel">17:00</div>'); return _d.time(17, 0)
    @staticmethod
    def form(*a, **k):
        b = _Box('<div data-testid="stForm" style="border:1px solid var(--p-border);border-radius:14px;padding:1rem">', "</div>"); _emit(b); return b
    @staticmethod
    def form_submit_button(label, type="secondary", icon=None, disabled=False, **k):
        _emit(f'<button kind="{type}" {"disabled" if disabled else ""}><p>{H.escape(label)}</p></button>'); return False
    @staticmethod
    def multiselect(label, options, default=None, **k):
        _emit(f'<div class="pp-label">{H.escape(label)}</div><div class="sel">{H.escape(", ".join(default or []) or "Choose options")}</div>'); return default or []
    @staticmethod
    def number_input(label, mn=0, mx=100, value=0, *a, **k):
        _emit(f'<div class="pp-label">{H.escape(label)}</div><div class="sel">{value}</div>'); return value
    @staticmethod
    def text_input(label, value="", **k):
        _emit(f'<div class="pp-label">{H.escape(label)}</div><div class="sel">{H.escape(str(value)) or "&nbsp;"}</div>'); return value
    text_area = text_input
    @staticmethod
    def metric(label, value, **k):
        _emit(f'<div data-testid="stMetric" style="padding:.3rem 0"><div class="pp-label">{H.escape(str(label))}</div><div style="font-size:1.8rem;font-weight:800">{H.escape(str(value))}</div></div>')
    @staticmethod
    def spinner(*a, **k): return _Box("", "")
    @staticmethod
    def download_button(label, *a, **k):
        _emit(f'<button kind="secondary"><p>{H.escape(label)}</p></button>'); return False
    @staticmethod
    def info(t, **k): _emit(f'<div data-testid="stAlert" style="padding:.7rem 1rem;background:var(--p-primary-soft);border-radius:12px">{H.escape(str(t))}</div>')
    warning = info
    def __getattr__(self, n):
        if n.startswith("__"): raise AttributeError(n)
        return lambda *a, **k: None


st = St("streamlit"); sys.modules["streamlit"] = st
for name in ("groq", "ddgs", "faiss", "sentence_transformers"):
    m = types.ModuleType(name); m.Groq = object; m.DDGS = object; m.SentenceTransformer = object; sys.modules[name] = m
import config  # noqa: E402
config.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "preview.db"
import login_ui, career_pages, career_profile, diary, diary_pages, plan_pages, classes, daily, db, goals, navigation, progress, theme, ui_kit as k, dashboard_pages, predictor_pages, leaderboard_pages, game_pages  # noqa: E402
db.init_db()


def Q(i, ok="A"):
    return {"question": f"Preview question {i}?", "options": {"A": "a", "B": "b", "C": "c", "D": "d"}, "answer": ok, "concept": f"c{i}", "explanation": "e", "difficulty": "Medium"}


def seed_full() -> str:
    db.ensure_student("prev_full", "Muhammad Shahzaib")
    db.update_student("prev_full", exam_name="MDCAT", exam_date=(datetime.utcnow() + timedelta(days=62)).date().isoformat(), goal_university="Allama Iqbal Medical College Lahore", goal_score=165, goal_scale=180)
    for i, (nm, right) in enumerate((("Sana Ahmed Raza", 10), ("zainab@example.com", 8), ("Hamza Tariq", 6), ("Bilal", 7))):
        sid = f"prev_o{i}"; db.ensure_student(sid, nm)
        for j in range(2): db.record_quiz(sid, "Biology", "Cells", [Q(f"o{i}{j}{x}") for x in range(10)], {x: ("A" if x < right else "B") for x in range(10)}, "Medium")
    for subj, topic, right in (("Biology", "Cell cycle", 9), ("Biology", "Genetics", 4), ("Chemistry", "Acids and bases", 8), ("Physics", "Kinematics", 3), ("English", "Vocabulary", 7)):
        qs = [Q(f"{topic}{i}") for i in range(10)]
        db.record_quiz("prev_full", subj, topic, qs, {i: ("A" if i < right else "B") for i in range(10)}, "Medium")
    db.save_plan("prev_full", "MDCAT 2026", "", [{"day": "Day 1", "sessions": [
        {"subject": "Biology", "topic": "Genetics - Mendelian ratios", "minutes": 30, "activity": "Read and make notes"},
        {"subject": "Chemistry", "topic": "Acids and bases - pH", "minutes": 25, "activity": "Practice MCQs"},
        {"subject": "Physics", "topic": "Kinematics - graphs", "minutes": 20, "activity": "Revise and self-test"}]}])
    import dashboard_data as dd
    dd.set_task_done("prev_full", progress.local_today(), f"plan:{dd.latest_plan('prev_full')['id']}:1:0", True)
    return "prev_full"


def seed_empty() -> str:
    db.ensure_student("prev_new", "Ayesha Khan"); return "prev_new"


NAV_VARIANT = "A"


def page(sid: str, title: str, body_fn, active: str = "Dashboard") -> str:
    STATE.clear(); OUT.clear(); TARGET[:] = [OUT]
    student = db.get_student(sid); p = progress.get_progress(sid)
    nav = []
    for group, items in navigation.groups(False):
        nav.append(f'<div class="pp-navlabel">{group}</div>')
        for route, icon in items:
            cls = "navon_" if route == active else "nav_"
            ic = f'<span data-testid="stIconMaterial" class="ic">{icon[:1].upper()}</span>'
            if NAV_VARIANT == "B": inner = f'<div data-testid="stMarkdownContainer"><p>{ic}{route}</p></div>'
            else: inner = f'{ic}<div data-testid="stMarkdownContainer"><p>{route}</p></div>'
            nav.append(f'<div class="st-key-{cls}{navigation.slug(route)}" data-testid="stElementContainer"><div data-testid="stButton"><button kind="secondary">{inner}</button></div></div>')
    days = None
    from dashboard_data import days_to_exam
    days = days_to_exam(student.get("exam_date"))
    g = goals.get_goal(student)
    if g["is_set"]:
        big, small = goals.describe(g)
        goal_html = k.sidebar_goal("Your goal", big, small + (" · " if small else "") + f"{p['today_questions']}/{p['goal']} questions today", p["goal_pct"])
    else:
        goal_html = k.sidebar_goal("Daily goal", f"{p['today_questions']} / {p['goal']}", f"{p['streak']}-day streak · Level {p['level']}", p["goal_pct"])
    goal = '<div data-testid="stMarkdownContainer" style="margin-bottom:-1rem">' + k.sidebar_header(goal_html) + '</div><div class="st-key-sb_edit_goal"><button><p>Edit goal</p></button></div>'
    nav = [x.replace('<div class="pp-navlabel">', '<div data-testid="stMarkdownContainer" style="margin-bottom:-1rem"><div class="pp-navlabel">', 1).replace("</div>", "</div></div>", 1) if x.startswith('<div class="pp-navlabel">') else x for x in nav]
    _emit('<div data-testid="stVerticalBlockBorderWrapper" class="st-key-topbar_row"><div class="cols" style="align-items:center;padding:.45rem .8rem;margin:0"><div class="col" style="flex:5">'
          + k.topbar(title, student["name"], [f"🔥 {p['streak']}-day streak", f"⭐ Level {p['level']}"], "", with_user=False)
          + '</div><div class="col st-key-profile_menu" style="flex:2"><button><span class="ic">A</span><p>' + H.escape(student["name"]) + '</p></button></div></div></div>')
    body_fn(sid, student["name"], student)
    main = _html(OUT)
    css = theme.build_css(config.UI_COLORS["Burgundy"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>{css}
    body{{margin:0}} .app{{display:flex;min-height:100vh}} [data-testid="stSidebar"]{{width:300px;flex:none;box-sizing:border-box;padding:.6rem .9rem}}
    section.stMain{{flex:1;min-width:0}} .cols{{display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:nowrap}} .col{{min-width:0}}
    button{{display:inline-flex;justify-content:center;align-items:center;gap:.5rem;cursor:pointer;font:inherit;padding:.45rem .8rem;border-radius:12px;border:1px solid var(--p-border);background:var(--p-card);color:var(--p-text)}}
    [data-testid="stVerticalBlockBorderWrapper"]{{padding:1rem;border:1px solid var(--p-border)}} label[data-baseweb="radio"] input{{margin:0}} label[data-baseweb="radio"] p{{margin:0}} button p{{margin:0}} .ic{{display:inline-grid;place-items:center;width:20px;height:20px;border-radius:6px;background:var(--p-primary-soft);color:var(--p-primary);font-size:.7rem;font-weight:800}}
    button [data-testid="stMarkdownContainer"]{{display:flex;justify-content:center}} [data-testid="stButton"]{{display:flex;justify-content:center}} [data-baseweb="input"]{{background:#fff;border:1px solid #ccc;border-radius:8px;padding:.3rem .6rem}} [data-baseweb="input"] input{{border:0;background:transparent;font:inherit;width:100%;outline:0}} [data-testid="stVerticalBlock"]>*{{margin-bottom:.5rem}} .st-key-topbar_row{{border:1px solid var(--p-border);border-radius:16px;background:var(--p-card);margin-bottom:1.1rem}} .cb{{display:flex;gap:.6rem;align-items:center;font-weight:600;padding:.25rem 0}}
    @media (max-width:900px){{.app{{flex-direction:column}} [data-testid="stSidebar"]{{width:auto;border-right:0;border-bottom:1px solid var(--p-border)}} .cols{{flex-direction:column}} .col{{flex:none!important}}}}
    </style></head><body class="stApp"><div class="app"><div data-testid="stSidebar">{goal}{"".join(nav)}</div>
    <section class="stMain"><div class="block-container">{main}</div></section></div>{navigation.badge_css("Mistakes Diary", diary.open_count(sid))}</body></html>"""


def login_doc(mode: str) -> str:
    """The split login screen with Streamlit-shaped DOM (keyed containers, columns, base-web inputs) so the real CSS is exercised."""
    def field(label, ph, kind="text"):
        return f'<div data-testid="stTextInput"><label><p>{label}</p></label><div data-baseweb="base-input"><div data-baseweb="input"><input type="{kind}" placeholder="{ph}"></div></div></div>'
    if mode == "login":
        form = ('<h1>Login</h1><p class="lg-note">Enter your account details</p><div data-testid="stForm">' + field("Email", "Email") + field("Password", "Password", "password")
                + '<div data-testid="stCaptionContainer"><p>Forgot your password? Ask the app administrator to reset it for you.</p></div><button kind="primaryFormSubmit" style="width:100%"><p>Log in</p></button></div>'
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:1.2rem"><span class="lg-note">Don\'t have an account?</span><div class="st-key-login_to_student"><button style="padding:.5rem 1.6rem"><p>Sign up</p></button></div></div>'
                '<div class="st-key-login_to_tutor"><button><p>Create a tutor account</p></button></div>')
    else:
        form = ('<h1>Sign up</h1><p class="lg-note">Create your student account. Your learning history and quiz performance stay private to you.</p><div data-testid="stForm">' + field("Full name", "Full name") + field("Email", "Email")
                + '<div style="display:flex;gap:1rem">' + field("Password (8+ characters, letters and numbers)", "", "password") + field("Confirm password", "", "password") + "</div>"
                + field("Current level", "MDCAT") + '<button kind="primaryFormSubmit" style="width:100%"><p>Create my student account</p></button></div>')
    css = theme.build_css(config.UI_COLORS["Burgundy"])
    return (f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>{css} body{{margin:0}} button{{font:inherit;cursor:pointer;padding:.5rem 1rem}} '
            f'[data-baseweb="input"]{{background:#fff;border:1px solid #ccc;border-radius:8px;padding:.45rem .7rem;margin-bottom:.8rem}} [data-baseweb="input"] input{{border:0;background:transparent;font:inherit;width:100%;outline:0}} '
            f'[data-testid="stForm"]{{border:1px solid #ddd;padding:1rem;border-radius:12px}} .block-container{{padding-top:1rem}}</style></head><body class="stApp"><div class="block-container">'
            f'<div class="st-key-login_split" data-testid="stVerticalBlock"><div data-testid="stHorizontalBlock" style="display:flex">'
            f'<div data-testid="stColumn" style="flex:1"><div class="st-key-login_left">{login_ui.brand_row()}{form}</div></div>'
            f'<div data-testid="stColumn" style="flex:1"><div data-testid="stMarkdownContainer">{login_ui.hero_panel()}</div></div></div></div></div></body></html>')


def main(out: pathlib.Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    full, empty = seed_full(), seed_empty()
    pages = {"dashboard_full": page(full, "Dashboard", lambda s, n, st_: dashboard_pages.render_top(s, n, st_)),
             "dashboard_empty": page(empty, "Dashboard", lambda s, n, st_: dashboard_pages.render_top(s, n, st_))}
    for name, doc in pages.items():
        (out / f"{name}.html").write_text(doc, encoding="utf-8")
    def radios(i, sel):
        opts = [("A", "Mitochondria"), ("B", "Ribosome"), ("C", "Golgi apparatus"), ("D", "Lysosome")]
        return ('<div data-testid="stRadio"><div role="radiogroup" aria-orientation="vertical">' + "".join(
            f'<label data-baseweb="radio"><input type="radio" name="q{i}" {"checked" if l == sel else ""}><div><p>{l}. {t}</p></div></label>' for l, t in opts) + "</div></div>")
    def quiz(sid, name, student):
        _emit(k.__dict__["greeting"] and '<div class="prep-hero"><h1>📝 Practice</h1><p>Practice current quizzes, weak topics, smart revision, mistakes and flashcards.</p></div>')
        _emit('<div data-testid="stMarkdownContainer"><p><b>Biology → Cell cycle</b> · Medium · 3 questions · ⏱ 05:00 limit</p></div>')
        _emit(k.qnav(3, {0}))
        for i, t in enumerate(["Which organelle is the main site of ATP production in a eukaryotic cell?", "Which stage of mitosis aligns chromosomes at the cell equator?", "Where are proteins assembled?"], 1):
            _emit(k.qcard(i, t)); _emit(radios(i, "A" if i == 1 else None))
        _emit('<div data-testid="stAlert" style="padding:.8rem 1rem;background:var(--p-ok-soft)">Correct answer: A</div>')
        _emit('<div data-testid="stProgress"><div role="progressbar"><div><div style="width:33%;height:8px"></div></div></div></div>')
        _emit('<button data-testid="stBaseButton-primary" kind="primary"><p>Submit Quiz</p></button> <button kind="secondary"><p>Download PDF</p></button>')
        _emit(k.badge("Correct", "ok") + " " + k.badge("Incorrect", "err") + " " + k.badge("Skipped", "warn"))
    pages["quiz"] = page(full, "Practice", quiz)
    pages["predictor"] = page(full, "Score Predictor", lambda s, n, st_: predictor_pages.render_predictor(s, st_), "Score Predictor")
    pages["predictor_empty"] = page(empty, "Score Predictor", lambda s, n, st_: predictor_pages.render_predictor(s, st_), "Score Predictor")
    pages["leaderboard"] = page(full, "Leaderboard", lambda s, n, st_: leaderboard_pages.render_leaderboard_page(s), "Leaderboard")
    pages["leaderboard_empty"] = page(empty, "Leaderboard", lambda s, n, st_: leaderboard_pages.render_leaderboard_page(s), "Leaderboard")
    import games as G, time as T
    def play(sid, name, student):
        qs = G.build_questions(sid, "Biology", 7, None, seed=3); run = G.new_run("quick", qs, "Biology", T.time() - 1.6, "p"); game_pages.st.session_state["game_run"] = run
        game_pages._play()
    pages["games_play"] = page(full, "Learning Games", lambda s, n, st_: (_emit(k.__dict__["greeting"] and '<div class="prep-hero"><h1>Learning Games</h1><p>Timed rounds</p></div>'), play(s, n, st_)), "Learning Games")
    pages["games"] = page(full, "Learning Games", lambda s, n, st_: game_pages.render_games(s, None, None, None), "Learning Games")
    def diary_body(sid, name, student):
        _emit('<div class="prep-hero"><h1>Mistakes Diary</h1><p>Every question you got wrong, in one place.</p></div>')
        items = diary.open_mistakes(sid); STATE[diary_pages.CUR] = items[0]["id"]
        STATE[diary_pages.TEXT] = {items[0]["id"]: "**Why your answer is wrong:** Kinematics graphs show velocity against time, so the slope is acceleration, not speed.\n\n**Why B is right:** the area under a v-t graph is displacement.\n\n**Memory trick:** slope = a, area = s.\n\n**Quick check:** what does a flat v-t line mean?"}
        diary_pages.render_diary(sid, None, None, None)
    pages["diary"] = page(full, "Mistakes Diary", diary_body, "Mistakes Diary")
    db.save_plan(full, "MDCAT 2026", "", [{"day": f"Day {d}", "sessions": [
        {"subject": "Biology", "topic": f"Genetics - Mendelian ratios {d}", "minutes": 60, "activity": "Read and make notes", "source": "Biology.pdf p.12"},
        {"subject": "Chemistry", "topic": "Acids and bases - pH", "minutes": 45, "activity": "Practice MCQs"},
        {"subject": "Physics", "topic": "Kinematics - graphs", "minutes": 40, "activity": "Revise and self-test"}]} for d in range(1, 10)])
    pages["plan"] = page(full, "Study Plan", lambda s, n, st_: plan_pages.render_saved_plan(s), "Study Plan")
    kb = __import__("pathfinder_service").load_kb()
    def wiz(step):
        def body(sid, name, student):
            _emit('<div class="prep-hero"><h1>🧭 Path Finder</h1><p>Step by step profile.</p></div>')
            STATE["cp_data"] = {"stream": "Pre-Medical", "interests": ["Medicine & healthcare"], "degree1": "MBBS", "degree2": "Pharm-D", "fsc_pct": 82.0, "universities": "KMU\nUHS", "backup": "Pharm-D at a public university",
                                "options": [{"name": "MBBS", "scores": {"interest": 5, "aptitude": 4, "career": 5, "afford": 3, "quality": 4, "lifestyle": 3, "training": 4}}, {"name": "Pharm-D", "scores": {"interest": 4, "aptitude": 4, "career": 3, "afford": 4, "quality": 3, "lifestyle": 4, "training": 5}}]}
            STATE["cp_step"] = step
            career_pages.render_wizard(sid, kb, {})
        return body
    pages["career_step1"] = page(full, "Path Finder", wiz(0), "Path Finder")
    pages["career_review"] = page(full, "Path Finder", wiz(8), "Path Finder")
    def rec(sid, name, student):
        data = {"stream": "Pre-Medical", "universities": "KMU\nUHS", "backup": "Pharm-D at a public university", "options": [{"name": "MBBS", "scores": {k_: 5 for k_, _, _ in career_profile.CRITERIA}}]}
        career_pages.render_recommendation(data, [p for p in kb["programs"][:3]] if False else __import__("pathfinder_service").match_programs(kb, career_profile.to_pf_profile(data)))
    pages["career_rec"] = page(full, "Path Finder", rec, "Path Finder")
    import dashboard_data as _dd
    _dd.set_task_done(full, progress.local_today(), f"plan:{_dd.latest_plan(full)['id']}:1:0", True)           # first session already done: its button must be green
    db.ensure_student("prev_tutor", "Dr Tutor"); db.set_role("prev_tutor", "tutor")
    cl_ = classes.create_class("prev_tutor", "MDCAT Junoon Batch"); classes.join_class(full, cl_["join_code"])
    code_ = db.create_shared_quiz("prev_tutor", "Cell Biology Weekly Quiz", "Biology", "Cells", "Medium", [Q(1)])
    classes.create_assignment("prev_tutor", cl_["id"], code_, "Cell Biology Weekly Quiz", (datetime.utcnow() + timedelta(days=1)).isoformat(timespec="minutes"))
    pages["schedule_full"] = page(full, "Dashboard", lambda s, n, st_: dashboard_pages.render_schedule(s), "Dashboard")
    global NAV_VARIANT
    NAV_VARIANT = "B"; pages["sidebar_variantB"] = page(full, "Dashboard", lambda s, n, st_: None, "Dashboard"); NAV_VARIANT = "A"
    pages["login"] = login_doc("login"); pages["signup"] = login_doc("student")
    for name, doc in pages.items():
        (out / f"{name}.html").write_text(doc, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for name in pages:
            for label, w, h in (("desktop", 1440, 1000), ("tablet", 820, 1100), ("mobile", 390, 844)):
                pg = br.new_page(viewport={"width": w, "height": h}); pg.goto((out / f"{name}.html").as_uri()); pg.wait_for_timeout(200)
                over = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                pg.screenshot(path=str(out / f"{name}_{label}.png"), full_page=True)
                print(f"{name} {label}: horizontal overflow = {over}px"); pg.close()
        br.close()


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "preview"))
