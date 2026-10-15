"""Headless run of app.py: every page is executed against a FAKE Streamlit (no browser, no API key).
Proves the new code is wired correctly (no NameError / bad arguments). It cannot judge how pages LOOK.
Run:  python tests/app_pages_smoke.py
"""
import contextlib, re, os, pathlib, sys, tempfile, types
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT, OVR = [], {}

class Rerun(Exception): pass
class Stop(Exception): pass
class State(dict):
    def __getattr__(self, k):
        try: return self[k]
        except KeyError: raise AttributeError(k)
    def __setattr__(self, k, v): self[k] = v

class Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, n): return getattr(FakeSt, n)

class FakeSt(types.ModuleType):
    session_state = State(); secrets = {}
    def __init__(self): super().__init__("streamlit")
    @staticmethod
    def _say(*a, **k): OUT.append(" ".join(str(x) for x in a if isinstance(x, (str, int, float))))
    markdown = write = caption = info = warning = error = success = subheader = title = code = toast = _say
    fragment = staticmethod(lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda f: f)))
    set_page_config = divider = staticmethod(lambda *a, **k: None)
    @staticmethod
    def stop(): raise Stop()
    @staticmethod
    def rerun(*a, **k): raise Rerun()
    @staticmethod
    def exception(e): raise e
    @staticmethod
    def fragment(*a, **k): return (lambda f: f) if not (a and callable(a[0])) else a[0]
    @staticmethod
    def cache_resource(*a, **k): return (lambda f: f) if not (a and callable(a[0])) else a[0]
    sidebar = Ctx()
    spinner = expander = form = container = chat_message = staticmethod(lambda *a, **k: Ctx())
    @staticmethod
    def columns(n, **k): return [Ctx() for _ in range(n if isinstance(n, int) else len(n))]
    @staticmethod
    def tabs(names): return [Ctx() for _ in names]
    @staticmethod
    def metric(label, value, **k): OUT.append(f"METRIC {label}={value}")
    @staticmethod
    def progress(v, text=None, **k):
        OUT.append(f"PROGRESS {text}")
        class _B:
            def progress(self, v, text=None, **k): OUT.append(f"PROGRESS {text}")
            def empty(self): pass
        return _B()
    @staticmethod
    def altair_chart(c, **k): OUT.append("CHART")
    @staticmethod
    def dataframe(d, **k): OUT.append("TABLE")
    @staticmethod
    def download_button(label, data, *a, **k): OUT.append(f"DOWNLOAD {label}")
    @staticmethod
    def radio(label, options=(), index=0, key=None, **k):
        opts = list(options); return OVR.get(key or label, opts[index] if (opts and index is not None) else None)
    @staticmethod
    def selectbox(label, options, index=0, key=None, **k): return OVR.get(key or label, list(options)[index or 0])
    @staticmethod
    def multiselect(label, options, key=None, default=None, **k): return OVR.get(key or label, default or [])
    @staticmethod
    def slider(label, min_value=0, max_value=100, value=None, key=None, **k):
        if min_value >= max_value: raise ValueError(f"StreamlitInvalidMinMaxError: slider {label!r} min {min_value} >= max {max_value}")      # what real Streamlit does
        if value is not None and not (min_value <= value <= max_value): raise ValueError(f"slider {label!r} value {value} outside {min_value}..{max_value}")
        return OVR.get(key or label, value if value is not None else min_value)
    @staticmethod
    def number_input(label, min_value=None, max_value=None, value=0, *a, key=None, **k): return OVR.get(key or label, value)
    @staticmethod
    def date_input(label, value=None, key=None, **k): return OVR.get(key or label, value)
    @staticmethod
    def text_input(label, value="", key=None, **k): return OVR.get(key or label, value)
    text_area = text_input
    @staticmethod
    def color_picker(label, value="#000000", key=None, **k): return OVR.get(key or label, value)
    @staticmethod
    def checkbox(label, value=False, key=None, **k): return OVR.get(key or label, FakeSt.session_state.get(key, value) if key else value)
    @staticmethod
    def button(label, key=None, on_click=None, args=(), **k):
        hit = OVR.get(key or label, False)
        if hit and on_click: on_click(*args)          # Streamlit runs the callback when the button is pressed
        return hit
    form_submit_button = button
    @staticmethod
    def time_input(label, value=None, key=None, **k): return OVR.get(key or label, value)
    popover = staticmethod(lambda *a, **k: Ctx())
    @staticmethod
    def link_button(label, url, **k): OUT.append(f"LINK {label}")
    @staticmethod
    def file_uploader(label, *a, key=None, **k): return OVR.get(key or label)
    @staticmethod
    def audio_input(*a, **k): return None
    @staticmethod
    def chat_input(*a, **k): return None

fake = FakeSt(); sys.modules["streamlit"] = fake
for n in ("groq", "ddgs", "faiss", "sentence_transformers", "gdown", "gtts", "altair"):
    m = mock.MagicMock(name=n); sys.modules[n] = m
import config
tmp = pathlib.Path(tempfile.mkdtemp()); config.DB_PATH = tmp / "t.db"; config.MEMORY_DIR = tmp / "mem"; config.MEMORY_DIR.mkdir()
import memory as _m
_m.embed_texts = lambda texts: __import__("numpy").ones((len(texts), 4), dtype="float32")
import rag as _rag; _rag.embed_texts = _m.embed_texts   # tutor document library embeds through rag.embed_texts

SRC = (ROOT / "app.py").read_text()
QS_OPT = [{"question": f"OptQ{i}", "options": {"A": "a", "B": "b", "C": "c", "D": "d"}, "answer": "A", "concept": "c", "explanation": "e", "difficulty": "Medium"} for i in range(3)]
QS = [{"question": f"Q{i}", "options": {"A": "a", "B": "b"}, "answer": "A", "concept": "c", "explanation": "e", "difficulty": "Medium"} for i in range(3)]

def run(page, **state):
    """Execute app.py once as a signed-in user viewing `page`."""
    OUT.clear()
    ss = fake.session_state
    ss.update({"profile_complete": True, "student_id": "stu1", "student_name": "Ali", **state})
    ss["nav_page"] = page.split(" (")[0]
    g = {"__name__": "__main__", "__file__": str(ROOT / "app.py")}
    try: exec(compile(SRC, "app.py", "exec"), g)
    except (Rerun, Stop): pass
    return g

failures = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  <- {detail}"))
    if not cond: failures.append(name)

import db
# ---- sign in as a new student, then visit every page
g = run("Dashboard")
check("dashboard renders (rings + donut charts)", OUT.count("CHART") >= 3, OUT[:5])
for p in ("Today", "Learn", "Practice", "Exam", "Mock Test", "My Classes", "Published Quizzes", "AI Tutor", "Merit Calculator", "Path Finder", "Study Plan", "Memory", "History", "Settings"):
    try:
        run(p); check(f"page '{p}' runs", True)
    except Exception as e:
        check(f"page '{p}' runs", False, repr(e))
run("Memory"); check("memory page shows usage meter", any("Memories stored" in o for o in OUT))
run("Settings"); check("settings has Appearance", any("Appearance" in o for o in OUT))

# ---- Today page: progress strip, goal, retake of past mistakes (no AI needed)
run("Today"); check("Today page shows streak/level/goal", any(o.startswith("METRIC 🔥 Streak") for o in OUT) and any(o.startswith("METRIC 🎯 Today") for o in OUT), OUT[:10])
run("Dashboard"); check("dashboard shows the greeting, streak and finish line", any("Assalam-o-Alaikum" in o for o in OUT) and any("day streak" in o for o in OUT) and any("Finish Line" in o for o in OUT), OUT[:8])
db.ensure_student("stu9", "Retaker")
db.record_quiz("stu9", "Biology", "Cells", QS_OPT, {0: "B", 1: "A", 2: "C"}, "Medium")
ss0 = fake.session_state
OVR["retake_btn"] = True; run("Today", student_id="stu9", student_name="Retaker", quiz=None); OVR.clear()
check("retake quiz starts from past mistakes", ss0["quiz"] and ss0["quiz"].get("origin") == "retake" and len(ss0["quiz"]["questions"]) == 2, ss0.get("quiz"))
uidr = ss0["quiz"]["uid"]; OVR["start_" + uidr] = True; run("Today", student_id="stu9", student_name="Retaker"); OVR.clear()
ss0["quiz"]["answers"] = {0: "A", 1: "A"}; OVR["submit_" + uidr] = True; run("Today", student_id="stu9", student_name="Retaker"); OVR.clear()
check("retake result earns XP and fixes the mistakes", ss0["quiz"]["result"] and ss0["quiz"]["result"].get("xp", 0) > 0 and db.progress.retakeable_mistakes("stu9") == [], ss0["quiz"].get("result"))
ss0["quiz"] = None; ss0["student_id"] = "stu1"; ss0["student_name"] = "Ali"

# ---- tutor navigation + dashboard
run("Dashboard", is_tutor=False); 
check("non-tutor cannot open tutor page", not any("Tutor Dashboard" in o and "METRIC" in o for o in OUT))
db.ensure_student("stu2", "Sara")
db.record_quiz("stu2", "Biology", "Cells", QS, {0: "A", 1: "A", 2: "B"}, "Medium")
_c0 = db.create_shared_quiz("stu1", "Scoped", "Biology", "Cells", "Medium", QS, 0)       # stu1 acts as the tutor here
db.record_quiz("stu2", "Biology", "Cells", QS, {0: "A", 1: "A", 2: "B"}, "Medium", shared_code=_c0, time_taken_sec=20)
run("Tutor Dashboard", is_tutor=True)
check("tutor dashboard shows class table + charts", "TABLE" in OUT and "CHART" in OUT and any(o.startswith("METRIC Students") for o in OUT), OUT[:8])
run("Tutor Dashboard", is_tutor=False); check("tutor page is not reachable for a non-tutor", fake.session_state["nav_page"] == "Dashboard" and not any("Create a quiz" in o for o in OUT), fake.session_state["nav_page"])

# ---- timed practice quiz: gate -> start -> auto-submit at expiry
import time
ss = fake.session_state
g = run("Practice", quiz=None)
quiz_mod = run("Practice")  # builds helpers in globals
new_quiz = quiz_mod["new_quiz"]
ss["quiz"] = new_quiz([dict(q) for q in QS], "Biology", "Cells", "Medium", [], 120)
run("Practice"); check("timed quiz waits for Start click", ss["quiz"]["started_at"] is None and any("Start Quiz" in o or "limit" in o for o in OUT), OUT[:6])
OVR["start_" + ss["quiz"]["uid"]] = True; run("Practice"); OVR.clear()
check("Start click begins the clock", ss["quiz"]["started_at"] is not None)
ss["quiz"]["answers"] = {0: "A", 1: "B"}; ss["quiz"]["answer_ts"] = {0: ss["quiz"]["started_at"] + 1, 1: ss["quiz"]["started_at"] + 2}
run("Practice"); check("quiz still open before the deadline", ss["quiz"]["result"] is None)
ss["quiz"]["started_at"] -= 500                                   # pretend 500s passed (limit 120s)
ss["quiz"]["answer_ts"] = {0: ss["quiz"]["started_at"] + 5, 1: ss["quiz"]["started_at"] + 400}   # Q2 picked AFTER the deadline
run("Practice")
res = ss["quiz"]["result"]
check("expired quiz is auto-submitted", res is not None and res["timed_out"] is True, res)
check("late answer is ignored, early one kept", res and res["correct"] == 1 and res["skipped"] == 2, res)
check("result saved in database as timed out", db.history("stu1")[0]["timed_out"] == 1 if db.history("stu1") else False)
run("Practice"); check("result screen shows score charts", OUT.count("CHART") >= 2, OUT[:6])
n_before = len(db.history("stu1")); run("Practice"); check("re-render never double-saves", len(db.history("stu1")) == n_before)

# ---- untimed quiz needs no Start click and manual submit works
ss["quiz"] = new_quiz([dict(q) for q in QS], "Biology", "Cells", "Medium", [], 0)
uid = ss["quiz"]["uid"]; run("Practice")
check("untimed quiz starts immediately", ss["quiz"]["started_at"] is not None)
ss["quiz"]["answers"] = {0: "A", 1: "A", 2: "A"}; OVR["submit_" + uid] = True; run("Practice"); OVR.clear()
check("manual submit scores 3/3", ss["quiz"]["result"] and ss["quiz"]["result"]["correct"] == 3 and not ss["quiz"]["result"]["timed_out"])

# ---- share + join
ss["quiz"] = new_quiz([dict(q) for q in QS], "Biology", "Cells", "Medium", [], 0)
uid = ss["quiz"]["uid"]; OVR["share_btn_" + uid] = True; run("Practice"); OVR.clear()
code = ss["quiz"].get("share_code_created")
check("share code created", bool(code) and len(code) == 6, code)
ss["student_id"] = "stu3"; ss["student_name"] = "Omar"; ss["shared_quiz"] = None
OVR["Quiz code"] = code; OVR["Open quiz"] = True; run("Published Quizzes", student_id="stu3", student_name="Omar"); OVR.clear()
check("student joins by code", ss["shared_quiz"] is not None and ss["shared_quiz"]["shared_code"] == code)
uid = ss["shared_quiz"]["uid"]; OVR["start_" + uid] = True; run("Published Quizzes", student_id="stu3", student_name="Omar"); OVR.clear()
ss["shared_quiz"]["answers"] = {0: "A", 1: "A", 2: "B"}; OVR["submit_" + uid] = True; run("Published Quizzes", student_id="stu3", student_name="Omar"); OVR.clear()
check("shared attempt saved under joiner's ID", [r["student_id"] for r in db.shared_quiz_results(code)] == ["stu3"])
ss["shared_quiz"] = None; OVR["Quiz code"] = code; OVR["Open quiz"] = True; run("Published Quizzes", student_id="stu3", student_name="Omar"); OVR.clear()
check("second attempt refused", ss["shared_quiz"] is None and any("already completed" in o for o in OUT), OUT[:4])

# ---- accounts: tutor/student sign-up and log-in screens
config.get_tutor_code = lambda: "secret-code"
def fresh_login_screen(mode="login", **ovr):
    OVR.clear(); OVR.update(ovr); OUT.clear(); ss.update({"profile_complete": False, "student_id": "", "user_id": None, "_cookie_checked": False, "login_mode": mode})
    g = {"__name__": "__main__", "__file__": str(ROOT / "app.py")}
    try: exec(compile(SRC, "app.py", "exec"), g)
    except (Rerun, Stop): pass
    OVR.clear()

tut = dict(tu_name="Dr Tutor", tu_email="tutor@example.com", tu_pw="Passw0rd!x", tu_pw2="Passw0rd!x")
fresh_login_screen("tutor", **tut, tu_invite="wrong", **{"Create my tutor account": True})
check("wrong tutor invite code refused", any("Incorrect tutor invite code" in o for o in OUT) and not ss["profile_complete"], OUT[:4])
fresh_login_screen("tutor", **{**tut, "tu_pw2": "different1"}, tu_invite="secret-code", **{"Create my tutor account": True})
check("mismatched passwords refused", any("do not match" in o for o in OUT) and not ss["profile_complete"], OUT[:4])
fresh_login_screen("tutor", **tut, tu_invite="secret-code", **{"Create my tutor account": True})
check("right invite code creates a tutor account and signs in", ss["profile_complete"] and ss["is_tutor"] and ss["student_id"].startswith("tutor_") and ss["user_id"], dict(ss))
TUTOR_ID = ss["student_id"]
fresh_login_screen("student", su_name="Ali Khan", su_email="ali@example.com", su_pw="Passw0rd!x", su_pw2="Passw0rd!x", su_level="MDCAT", **{"Create my student account": True})
check("student sign-up creates account and signs in", ss["profile_complete"] and not ss["is_tutor"] and ss["student_id"].startswith("stu_"), dict(ss))
STU_ID = ss["student_id"]
fresh_login_screen(login_email="ali@example.com", login_password="wrong-pass1", **{"Log in": True})
check("wrong password refused", any("Incorrect email or password" in o for o in OUT) and not ss["profile_complete"], OUT[:4])
fresh_login_screen(login_email="ALI@example.com", login_password="Passw0rd!x", **{"Log in": True})
check("log in restores the same student", ss["profile_complete"] and ss["student_id"] == STU_ID, dict(ss))
fresh_login_screen(login_email="tutor@example.com", login_password="Passw0rd!x", **{"Log in": True})
check("tutor logs in as tutor", ss["is_tutor"] and ss["student_id"] == TUTOR_ID, dict(ss))
# the new split login screen: login form by default, Sign up switches the form, the brand panel is always there
fresh_login_screen(); check("login screen shows Login, the brand panel, tagline and the Sign up switch", any("<h1>Login</h1>" in o for o in OUT) and any("Welcome to" in o and "Adaptive Multi-Agent Learning Platform" in o and "lg-art" in o for o in OUT), [o[:60] for o in OUT[:6]])
OVR["login_to_student"] = True; fresh_login_screen(**{"login_to_student": True}); check("Sign up switches the form to student sign-up", ss.get("login_mode") == "student")
fresh_login_screen("student"); check("sign-up screen shows its heading", any("<h1>Sign up</h1>" in o for o in OUT))
fresh_login_screen("tutor"); check("tutor sign-up screen shows its heading", any("Tutor sign up" in o for o in OUT))
OVR.clear()
navs = []
orig_button = FakeSt.button
def _nav_button(label, key=None, **k):
    if key and (key.startswith("nav_") or key.startswith("navon_")): navs.append((label, key.startswith("navon_"), k.get("icon")))
    return orig_button(label, key=key, **k)
FakeSt.button = staticmethod(_nav_button)
run("Tutor Dashboard", is_tutor=True, student_id=TUTOR_ID, student_name="Tutor")
check("tutor navigation is Tutor Dashboard and Settings", [n[0] for n in navs] == ["Tutor Dashboard", "Settings"] and navs[0][1], navs)
navs.clear(); run("Dashboard", is_tutor=False, student_id="stu1", student_name="Ali")
labels = [n[0] for n in navs]
check("student navigation has Published Quizzes, no Join Quiz/Tutor Dashboard", "Published Quizzes" in labels and "Join Quiz" not in labels and "Tutor Dashboard" not in labels, labels)
check("every sidebar item has an icon and exactly the active page is highlighted", all(n[2] and n[2].startswith(":material/") for n in navs) and [n[0] for n in navs if n[1]] == ["Dashboard"], navs)
import navigation as _nav
check("every sidebar item opens an existing route", all(r in re.findall(r'^    "([^"]+)": ', SRC.split("routes = {")[1], re.M) for r in _nav.routes(False) + _nav.routes(True)), _nav.routes(False))
FakeSt.button = staticmethod(orig_button)

# ---- tutor publishes from the dashboard; students get their own question order
tid = TUTOR_ID
ss["quiz"] = new_quiz([dict(q, question=f"Q{i}") for i, q in enumerate(QS * 4)], "Biology", "Cells", "Medium", [], 0)
uid = ss["quiz"]["uid"]; OVR["share_btn_" + uid] = True; run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
tcode = ss["quiz"].get("share_code_created")
check("tutor publishes a quiz from the dashboard", bool(tcode) and [q["code"] for q in db.list_shared_quizzes(tid)] == [tcode], (tcode, tid, [q["code"] for q in db.list_shared_quizzes()]))
orders = []
for sid in ("a1", "b2", "c3", "d4"):
    ss["shared_quiz"] = None; OVR["Quiz code"] = tcode; OVR["Open quiz"] = True
    run("Published Quizzes", student_id=sid, student_name=sid, is_tutor=False); OVR.clear()
    orders.append(tuple(q["question"] for q in ss["shared_quiz"]["questions"]))
check("same questions for everyone", len({tuple(sorted(o)) for o in orders}) == 1)
check("each student gets a different order", len(set(orders)) > 1, orders)
ss["shared_quiz"] = None
run("Published Quizzes", student_id="a1", student_name="a1", is_tutor=False)
check("students see results as locked", any("visible only to the tutor" in o for o in OUT), OUT[:6])

# ---- question bank, editor and option shuffling (tutor flow)
import bank, question_tools as _qt
for i, q in enumerate(QS_OPT * 3):                                    # 9 distinct 4-option questions
    bank.add_question(tid, dict(q, question=f"Bank question number {i} about cells?"), "Biology", "Cells")
OVR["bq_go"] = True; OVR["bq_n"] = 6; OVR["bq_subject"] = "Biology"
ss["quiz"] = None; run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
check("tutor builds a quiz from the bank", ss["quiz"] and len(ss["quiz"]["questions"]) == 6, ss.get("quiz"))
quid = ss["quiz"]["uid"]
OVR[f"ed_{quid}_0_0_q"] = "EDITED: which organelle makes ATP in the cell?"; OVR[f"ed_{quid}_0_0_ans"] = "C"; OVR[f"ed_{quid}_0_1_del"] = True
OVR["Apply edits"] = True; run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
check("editor applies text/answer edits and removes a question", len(ss["quiz"]["questions"]) == 5 and ss["quiz"]["questions"][0]["question"].startswith("EDITED") and ss["quiz"]["questions"][0]["answer"] == "C", [q["question"][:20] for q in ss["quiz"]["questions"]])
OVR[f"ed_{quid}_1_0_ans"] = "Z"
# an invalid edit must not be applied
n_before = len(ss["quiz"]["questions"]); OVR[f"ed_{quid}_1_1_A"] = ""; OVR["Apply edits"] = True
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
check("invalid edit is refused and the old question kept", len(ss["quiz"]["questions"]) == n_before and all(not _qt.validate_question(q) for q in ss["quiz"]["questions"]), OUT[-4:])
quid = ss["quiz"]["uid"]; OVR["share_btn_" + quid] = True; run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
ocode = ss["quiz"].get("share_code_created"); check("edited quiz published", bool(ocode))
letters_of_correct = []
for sid in ("o1", "o2", "o3", "o4", "o5", "o6"):
    ss["shared_quiz"] = None; OVR["Quiz code"] = ocode; OVR["Open quiz"] = True
    run("Published Quizzes", student_id=sid, student_name=sid, is_tutor=False); OVR.clear()
    qz = ss["shared_quiz"]; texts = {q["question"]: q["options"][q["answer"]] for q in qz["questions"]}
    orig = {q["question"]: q["options"][q["answer"]] for q in db.get_shared_quiz(ocode)["questions"]}
    if sid == "o1": check("shuffle keeps the correct TEXT correct for every question", texts == orig, (texts, orig))
    letters_of_correct.append(tuple(q["answer"] for q in sorted(qz["questions"], key=lambda q: q["question"])))
    OVR["start_" + qz["uid"]] = True; run("Published Quizzes", student_id=sid, student_name=sid, is_tutor=False); OVR.clear()
    qz["answers"] = {i: q["answer"] for i, q in enumerate(qz["questions"])}; OVR["submit_" + qz["uid"]] = True
    run("Published Quizzes", student_id=sid, student_name=sid, is_tutor=False); OVR.clear()
    if sid == "o1": check("a student answering by the shuffled letters scores 100%", qz["result"] and qz["result"]["pct"] == 100.0, qz.get("result"))
check("different students see different option orders", len(set(letters_of_correct)) > 1, letters_of_correct)

# ---- mock test mode
import mock as _mock, classes as _cls
from datetime import date as _d, time as _t, timedelta as _td
for subj in ("Biology", "Chemistry"):
    for i in range(6):
        bank.add_question("mk1", dict(QS_OPT[0], question=f"Mock {subj} question number {i} here?"), subj, "T")
run("Mock Test", student_id="mk1", student_name="Mk"); check("Mock Test page runs", any("Mock Test" in o for o in OUT), OUT[:4])
OVR.update({"mk_type": "Custom", "mk_c_Biology": 4, "mk_c_Chemistry": 3, "mk_c_Physics": 0, "mk_c_English": 0, "mk_c_Logical Reasoning": 0, "mk_ai": False, "mk_build": True})
ss["mock"] = None; run("Mock Test", student_id="mk1", student_name="Mk"); OVR.clear()
mq = ss.get("mock"); check("mock test is built from the bank", mq and len(mq["questions"]) == 7, mq and len(mq["questions"]))
check("mock progress saved for resume", _mock.load_progress("mk1") is not None)
OVR["mk_start_" + mq["uid"]] = True; run("Mock Test", student_id="mk1", student_name="Mk"); OVR.clear()
check("mock clock starts on click", mq["started_at"] is not None)
mq["answers"] = {i: q["answer"] for i, q in enumerate(mq["questions"][:5])}; mq["answer_ts"] = {i: mq["started_at"] + 1 for i in mq["answers"]}
OVR["mk_submit_" + mq["uid"]] = True; run("Mock Test", student_id="mk1", student_name="Mk"); OVR.clear()
check("mock result has section scores and is saved", mq["result"] and mq.get("scores") and len(_mock.history("mk1")) == 1 and _mock.load_progress("mk1") is None, mq.get("result"))
ss["mock"] = None

# ---- classes with deadlines
cl = _cls.create_class(tid, "Morning batch")
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); check("tutor Classes tab renders", any("Classes and deadlines" in o for o in OUT), OUT[:5])
ok, _m_, _c = _cls.join_class("cs1", cl["join_code"]); check("student joins class by code", ok)
dcode = db.create_shared_quiz(tid, "Due quiz", "Biology", "Cells", "Medium", QS, 0)
soon = _cls.local_to_utc_iso(_d.today() + _td(days=2), _t(12, 0))
check("assignment with future deadline created", _cls.create_assignment(tid, cl["id"], dcode, "", soon, False)[0])
ss["shared_quiz"] = None
try: run("My Classes", student_id="cs1", student_name="Cs", is_tutor=False)
except Exception as e: import traceback; traceback.print_exc()
check("My Classes lists the assignment", any("Due quiz" in o or "due" in o for o in OUT), OUT[6:])
ss["shared_quiz"] = None; OVR["Quiz code"] = dcode; OVR["Open quiz"] = True; run("Published Quizzes", student_id="cs1", student_name="Cs", is_tutor=False); OVR.clear()
check("student can open the assigned quiz before the deadline", ss["shared_quiz"] is not None)
import sqlite3
with db.connect() as _con: _con.execute("UPDATE assignments SET due_at=? WHERE quiz_code=?", ("2020-01-01T00:00", dcode))
ss["shared_quiz"] = None; OVR["Quiz code"] = dcode; OVR["Open quiz"] = True; run("Published Quizzes", student_id="cs1", student_name="Cs", is_tutor=False); OVR.clear()
check("late start is blocked after the deadline", ss["shared_quiz"] is None and any("deadline" in o for o in OUT), OUT[:4])
ss["shared_quiz"] = None; OVR["Quiz code"] = dcode; OVR["Open quiz"] = True; run("Published Quizzes", student_id="outsider", student_name="Out", is_tutor=False); OVR.clear()
check("students outside the class are not bound by the deadline", ss["shared_quiz"] is not None)
ss["shared_quiz"] = None
with db.connect() as _con: _con.execute("UPDATE assignments SET allow_late=1 WHERE quiz_code=?", (dcode,))
OVR["Quiz code"] = dcode; OVR["Open quiz"] = True; run("Published Quizzes", student_id="cs1", student_name="Cs", is_tutor=False); OVR.clear()
check("allow-late lets the student start (with a warning)", ss["shared_quiz"] is not None and any("late" in o for o in OUT), OUT[:4])
ss["shared_quiz"] = None

# ---- Month 2: daily challenge, live quiz, reminders, AI quality tab
import daily as _daily, live as _live
OVR.clear(); ss["daily_quiz"] = None
run("Daily Challenge", student_id="dc1", student_name="Dee", is_tutor=False); check("Daily Challenge page runs", any("Daily Challenge" in o for o in OUT), OUT[:3])
OVR["daily_start"] = True; run("Daily Challenge", student_id="dc1", student_name="Dee", is_tutor=False); OVR.clear()
dq = ss.get("daily_quiz"); check("daily challenge builds 5 questions offline", dq and len(dq["questions"]) == 5 and dq["time_limit_sec"] == 300, dq and len(dq["questions"]))
OVR["start_" + dq["uid"]] = True; run("Daily Challenge", student_id="dc1", student_name="Dee", is_tutor=False); OVR.clear()
dq["answers"] = {i: q["answer"] for i, q in enumerate(dq["questions"])}; dq["answer_ts"] = {i: dq["started_at"] + 1 for i in dq["answers"]}
OVR["submit_" + dq["uid"]] = True; run("Daily Challenge", student_id="dc1", student_name="Dee", is_tutor=False); OVR.clear()
run("Daily Challenge", student_id="dc1", student_name="Dee", is_tutor=False)   # the app re-runs once after submit and stores the day's result then
res_d = _daily.result_for("dc1", _daily.today())
check("daily result stored with bonus XP", res_d and res_d["correct"] == 5 and res_d["xp"] == _daily.BONUS_XP + _daily.BONUS_PERFECT, res_d)
run("Daily Challenge", student_id="dc1", student_name="Dee", is_tutor=False); check("page shows done + leaderboard after finishing", any("already done" in o or "challenge is done" in o for o in OUT) and "TABLE" in OUT, OUT[:6])
ss["daily_quiz"] = None
OVR["daily_start"] = True; run("Daily Challenge", student_id="dc1", student_name="Dee", is_tutor=False); OVR.clear()
check("second attempt on the same day is not offered", ss.get("daily_quiz") is None)

# live quiz: tutor creates from the bank, student joins and answers
for i in range(3): bank.add_question(tid, dict(QS_OPT[0], question=f"Live bank question {i} about the cell?"), "Biology", "Cells")
OVR.update({"lv_create": True, "lv_subject": "Biology", "lv_n": 3}); ss["live_host_code"] = None
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
lcode = ss.get("live_host_code"); check("tutor creates a live quiz", bool(lcode) and len(lcode) == 6, lcode)
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); check("host console shows the join code", any(lcode in o for o in OUT), OUT[:5])
ss["live_code"] = None; OVR["Live quiz code"] = lcode; OVR["Join"] = True
run("Live Quiz", student_id="lp1", student_name="Pat", is_tutor=False); OVR.clear()
check("student joins the live quiz", ss.get("live_code") == lcode)
run("Live Quiz", student_id="lp1", student_name="Pat", is_tutor=False); check("student waits in the lobby", any("Waiting for the tutor" in o for o in OUT), OUT[:5])
OVR["lv_start"] = True; run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
check("host starts the game", _live.get_state(lcode)["state"] == _live.QUESTION)
run("Live Quiz", student_id="lp1", student_name="Pat", is_tutor=False); check("student sees the question", any("Question 1 of 3" in o for o in OUT), OUT[:6])
sid_l = _live.get_state(lcode)["id"]; q0 = _live.get_questions(sid_l)[0]
shown = _live.display_question(q0, "lp1", sid_l); pressed = next(k for k, v in shown["options"].items() if v == q0["options"][q0["answer"]])
OVR[f"lvp_{sid_l}_0_{pressed}"] = True; run("Live Quiz", student_id="lp1", student_name="Pat", is_tutor=False); OVR.clear()
check("correct answer by shuffled letter scores points", (_live.my_answer(sid_l, "lp1", 0) or {}).get("is_correct") == 1, _live.my_answer(sid_l, "lp1", 0))
run("Live Quiz", student_id="lp1", student_name="Pat", is_tutor=False); check("student sees answer locked", any("locked" in o for o in OUT), OUT[:6])
_live.end_session(lcode, tid); run("Live Quiz", student_id="lp1", student_name="Pat", is_tutor=False)
check("finished game shows the result and credits progress", any("over" in o for o in OUT) and len(db.history("lp1")) == 1, OUT[:5])
ss["live_code"] = None; ss["live_host_code"] = None

# reminders + AI quality
OVR["rem_preview"] = True; run("Today", student_id="dc1", student_name="Dee", is_tutor=False); OVR.clear()
check("reminder preview works", any(o.startswith("LINK") for o in OUT) or any("caught up" in o for o in OUT), OUT[-4:])
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); check("AI Quality tab renders", any("AI quality" in o for o in OUT), OUT[:3])
OVR["aiq_import"] = True; run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
check("starter pack imported into the bank", bank.count_questions(tid, subject="Chemistry") >= 10, bank.count_questions(tid))

# ---- Month 3: quiz from the tutor's own document, PDF assignments
import io as _io, pdf_assignments as _pa, agent_system as _ag
class _Up:
    def __init__(self, name, data): self.name, self._d = name, data
    def getvalue(self): return self._d
def _pdf(text="Cells are the basic unit of life. " * 40):
    from reportlab.pdfgen import canvas
    b = _io.BytesIO(); c = canvas.Canvas(b); y = 800
    for k in range(0, len(text), 90): c.drawString(40, y, text[k:k + 90]); y -= 14
    c.showPage(); c.save(); return b.getvalue()
_ag.AssessmentAgent.generate_mcqs = lambda self, ctx, mem, count=10, avoid=None: [dict(QS_OPT[0], question=f"From the document {abs(hash(ctx.rag_context[:50]))} question {i}, which part?") for i in range(count)]
DOC = ("Mitochondria produce energy for the cell. " * 80 + "Ribosomes build proteins from amino acids. " * 80).encode()
ss["quiz"] = None
OVR.update({"tq_source": "My own document", "tq_files": [_Up("notes.txt", DOC)], "tq_count": 10, "tq_generate": True})
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
dqz = ss.get("quiz"); check("tutor generates a quiz from an uploaded document", dqz and dqz.get("from_document") and len(dqz["questions"]) == 10, dqz and len(dqz["questions"]))
OVR.update({"tq_source": "My own document", "tq_files": [_Up("bad.pdf", b"not really a pdf")], "tq_generate": True}); ss["quiz"] = None
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
check("an unreadable document gives a clear message and no quiz", ss.get("quiz") is None and any("could not be read" in o for o in OUT), OUT[-3:])
# tutor document library: process once, reuse without uploading, search preview, other tutor sees nothing, delete
import tutor_docs as _td
CHEM = ("Le Chatelier principle describes how chemical equilibrium shifts. " * 40 + "Sodium chloride has a molar mass of 58.44 grams per mole. " * 40).encode()
ss["quiz"] = None; ss.pop("tq_docs", None)
OVR.update({"tq_source": "My own document", "tq_files": [_Up("chem.txt", CHEM)], "tq_process": True})
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
lib = _td.list_documents(tid); chem = [d for d in lib if d["title"] == "chem"]
check("process button saves the document to the library", len(chem) == 1 and chem[0]["chunk_count"] >= 2, [d["title"] for d in lib])
check("progress is shown while processing", any(o.startswith("PROGRESS Creating embeddings") for o in OUT), OUT[:6])
OVR.update({"tq_source": "My own document", "tq_docs": [chem[0]["id"]], "tq_count": 5, "tq_topic": "Chatelier", "tq_search_label": "Keyword (exact words)", "tq_generate": True})
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
rq = ss.get("quiz"); check("quiz from a saved document needs no new upload", rq and rq.get("from_document") and len(rq["questions"]) == 5, rq and len(rq["questions"]))
other = "tutor_other"; db.ensure_student(other, "Other"); db.set_role(other, "tutor")
check("another tutor's library is empty", _td.list_documents(other) == [])
ss["quiz"] = None; ss.pop("tq_docs", None)
_btn = FakeSt.button; _cap = {}
FakeSt.button = staticmethod(lambda label, key=None, **k: _cap.setdefault(label, k) and False)
OVR.update({"tq_source": "My own document"})
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear(); FakeSt.button = staticmethod(_btn)
dcb = _cap.get("Delete this document", {})
check("delete button is wired with the chosen document", callable(dcb.get("on_click")) and dcb.get("args") and dcb["args"][0] in [d["id"] for d in _td.list_documents(tid)], dcb)
dcb["on_click"](*dcb["args"])
check("deleting removes the document and its sections", not [d for d in _td.list_documents(tid) if d["title"] == "chem"])

pc = _cls.create_class(tid, "PDF class"); _cls.join_class("pdfs1", pc["join_code"]); db.ensure_student("pdfs1", "Pdf Student")
OVR.update({f"cls_kind_{pc['id']}": "PDF assignment", f"cls_pdf_file_{pc['id']}": _Up("hw.pdf", _pdf()), "Title": "Homework A", "Assign PDF": True})
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
rep = [r for r in _cls.list_assignments(tid, pc["id"]) if r["kind"] == "pdf"]
check("tutor assigns a PDF from the Classes tab", len(rep) == 1 and rep[0]["title"] == "Homework A", rep and rep[0]["title"])
aid = rep[0]["id"]
run("My Classes", student_id="pdfs1", student_name="Pdf Student", is_tutor=False)
check("student sees the PDF assignment with an upload box", any("Homework A" in o for o in OUT) and any("Not submitted" in o or "Due soon" in o for o in OUT), OUT[6:12])
OVR.update({f"asg_up_{aid}": _Up("solution.pdf", _pdf("My answer is mitochondria. " * 30)), f"asg_submit_{aid}": True})
run("My Classes", student_id="pdfs1", student_name="Pdf Student", is_tutor=False); OVR.clear()
check("student uploads a solution PDF", _pa.my_submission("pdfs1", aid) is not None)
OVR.update({f"asg_up_{aid}": _Up("virus.pdf", b"MZ not pdf"), f"asg_submit_{aid}": True})
run("My Classes", student_id="pdfs1", student_name="Pdf Student", is_tutor=False); OVR.clear()
check("a non-PDF upload is rejected and the old solution stays", _pa.my_submission("pdfs1", aid)["filename"] == "solution.pdf")
row = [r for r in _cls.assignment_report(tid, aid)["rows"] if r["student_id"] == "pdfs1"][0]
OVR.update({f"asg_who_{aid}": row, "Marks": 8.0, "Save marks": True})
run("Tutor Dashboard", is_tutor=True, student_id=tid, student_name="Tutor"); OVR.clear()
check("tutor marks the solution", _pa.my_submission("pdfs1", aid)["marks"] == 8.0, _pa.my_submission("pdfs1", aid))
run("My Classes", student_id="pdfs1", student_name="Pdf Student", is_tutor=False)
check("student sees the mark and the upload is locked", any("Marks" in o for o in OUT) and any("locked" in o for o in OUT), OUT[6:14])

# ---- Study plan from chapters (database / own documents) and the unchanged quiz-history plan
import agent_system as _ag2, rag as _rag2
def _plan_json(prompt):
    _plan_json.prompts.append(prompt)
    return {"days": [{"day": f"Day {i}", "sessions": [{"subject": "Biology", "topic": "Genetics - alleles", "minutes": 30, "activity": "Read and make notes", "source": "bio.pdf p.12"}]} for i in range(1, 8)]}
_plan_json.prompts = []
_ag2.generate_json = _plan_json
_MD = [{"text": "Genetics: genes are inherited in Mendelian ratios. " * 5, "filename": "bio.pdf", "page": 12, "subject": "Biology"}, {"text": "Chemistry text about moles. " * 5, "filename": "chem.pdf", "page": 2, "subject": "Chemistry"}]
class _Ix: ntotal = 2
_rag2.load_database_index = lambda: (_Ix(), _MD)
def _hs(q, chunks, index, k=6):
    words = [w for w in q.lower().split() if len(w) > 3 and w != "biology"]
    return [dict(c, hybrid_score=0.8) for c in chunks if any(w in c["text"].lower() for w in words)][:k]
_rag2.hybrid_search = _hs
ss["study_plan"] = []
OVR.update({"plan_source": "My quiz history (weak topics)", "Create My Study Plan": True}); run("Study Plan", student_id="sp1", student_name="Sam", is_tutor=False); OVR.clear()
check("quiz-history plan still works", len(ss.get("study_plan", [])) == 7 and "weak topics from learning profile" in _plan_json.prompts[-1].lower(), len(ss.get("study_plan", [])))
_plan_json.prompts.clear(); ss["study_plan"] = []
OVR.update({"plan_source": "Chapters from the Prep.AI database", "plan_subject": "Biology", "plan_chapters": "Genetics\nNoSuchChapter", "plan_make": True})
run("Study Plan", student_id="sp1", student_name="Sam", is_tutor=False); OVR.clear()
check("chapter plan is created from the database", len(ss.get("study_plan", [])) == 7 and "genes are inherited" in _plan_json.prompts[-1] and "Chemistry text" not in _plan_json.prompts[-1], _plan_json.prompts[-1][:80] if _plan_json.prompts else None)
check("a chapter that is not in the material is reported", any(k == "warning" and "NoSuchChapter" in t for k, t in ss.get("study_plan_notes", [])), ss.get("study_plan_notes"))
with db.connect() as _c: _saved = _c.execute("SELECT plan_json FROM study_plans WHERE student_id='sp1' ORDER BY id DESC LIMIT 1").fetchone()
check("chapter plan is saved", _saved is not None and "bio.pdf p.12" in _saved[0], _saved)
run("Study Plan", student_id="sp1", student_name="Sam", is_tutor=False); check("plan shows its source page", any("bio.pdf p.12" in o for o in OUT), OUT[-6:])
def _down(prompt): raise RuntimeError("AI down")
_ag2.generate_json = _down; ss["study_plan"] = []
OVR.update({"plan_source": "Chapters from the Prep.AI database", "plan_subject": "Biology", "plan_chapters": "Genetics", "plan_make": True, "plan_days": 5})
run("Study Plan", student_id="sp1", student_name="Sam", is_tutor=False); OVR.clear()
check("plan still built when the AI is down", len(ss.get("study_plan", [])) == 5 and any(k == "info" and "unavailable" in t for k, t in ss.get("study_plan_notes", [])), ss.get("study_plan_notes"))
_ag2.generate_json = _plan_json; ss["study_plan"] = []
OVR.update({"plan_source": "Chapters from the Prep.AI database", "plan_subject": "Biology", "plan_chapters": "Nothing here", "plan_make": True})
run("Study Plan", student_id="sp1", student_name="Sam", is_tutor=False); OVR.clear()
check("no chapter found gives a clear error and no plan", ss.get("study_plan") == [] and any("None of those chapters" in o for o in OUT), OUT[-3:])
OVR.update({"plan_source": "Chapters from my own documents", "plan_chapters": "Genetics", "plan_make": True}); ss["personal_chunks"] = []; ss["personal_index"] = None
run("Study Plan", student_id="sp1", student_name="Sam", is_tutor=False); OVR.clear()
check("own-document plan asks for a processed document first", any("process your documents" in o.lower() for o in OUT) and ss.get("study_plan") == [], OUT[-3:])
NOTES = ("Meiosis halves the chromosome number in gametes. " * 30 + "Genetics studies heredity and genes. " * 30).encode()
OVR.update({"plan_source": "Chapters from my own documents", "plan_files": [_Up("notes.txt", NOTES)], "plan_process": True}); run("Study Plan", student_id="sp1", student_name="Sam", is_tutor=False); OVR.clear()
check("documents are processed for the plan", len(ss["personal_chunks"]) >= 1 and ss["personal_info"][0]["filename"] == "notes.txt", ss.get("personal_info"))
_plan_json.prompts.clear()
OVR.update({"plan_source": "Chapters from my own documents", "plan_doc_subject": "Biology", "plan_chapters": "Genetics", "plan_make": True}); run("Study Plan", student_id="sp1", student_name="Sam", is_tutor=False); OVR.clear()
check("plan is built from the student's own document", len(ss.get("study_plan", [])) == 7 and "Meiosis halves" in _plan_json.prompts[-1], _plan_json.prompts[-1][:60] if _plan_json.prompts else None)

# ---- memory reset button
from memory import LongTermMemory
ss["student_id"] = "stu1"; ss["student_name"] = "Ali"
for i in range(3): LongTermMemory("stu1").add(f"memory item {i} about cells", "learning")
check("memory exists before reset", LongTermMemory("stu1").count() == 3)
# the button callback is passed to st.button(on_click=...): capture and invoke it
captured = {}
orig_button = FakeSt.button
FakeSt.button = staticmethod(lambda label, key=None, **k: captured.setdefault(label, k.get("on_click")) and False)
ss["reset_confirm"] = True; ss["reset_incl_chats"] = False
run("Memory"); FakeSt.button = staticmethod(orig_button)
cb = captured.get("Reset my memory now"); check("reset button wired with callback", callable(cb))
cb(); check("callback empties memory", LongTermMemory("stu1").count() == 0)
check("confirmation box un-ticks itself", ss["reset_confirm"] is False)
run("Memory"); check("page tells the user what was removed", any("Memory reset" in o for o in OUT), OUT[:5])

# ---- theme applied
db.update_preferences("stu1", theme_preset="Dark")
for k in ("theme_preset", "theme_bg", "theme_text"): ss.pop(k, None)
run("Dashboard"); check("saved Dark theme loads and reaches charts", ss["theme_pair"] == ("#0E1117", "#F3F4F6"), ss.get("theme_pair"))

# ---- v5.2: new pages, editable goal, games, leaderboard
for p in ("Learning Games", "Leaderboard", "Score Predictor", "Daily Challenge"):
    try: run(p); check(f"v5.2 page '{p}' runs", True)
    except Exception as e: check(f"v5.2 page '{p}' runs", False, repr(e))
run("Leaderboard"); check("leaderboard honest empty state or real rows", any(("Nobody has earned points" in o) or ("pp-lb" in o) for o in OUT), OUT[:6])
run("Score Predictor"); check("predictor shows empty state with no data", any("Answer" in o and "unlock your estimate" in o for o in OUT), OUT[:8])
run("Learning Games"); check("games page lists both games", any("Quick MCQ Challenge" in o for o in OUT) and any("Rapid Fire" in o for o in OUT))
import datetime as _dt
# start Quick MCQ Challenge: real starter-set questions, 10 s each, count chosen by the student
OVR["game_play_quick"] = True; OVR["game_subject_quick"] = "Biology"; OVR["game_n_quick"] = 7
try: run("Learning Games")
except Exception as e: check("game start", False, repr(e))
gr = fake.session_state.get("game_run")
check("starting Quick creates a 7-question, 10-second run", bool(gr) and gr["game"] == "quick" and len(gr["questions"]) == 7 and gr["per_q"] == 10, gr and gr["game"])
OVR.pop("game_play_quick")
run("Learning Games"); check("play screen shows the question and a countdown", any("Question 1 of 7" in o for o in OUT), OUT[:6])
import games as _g, time as _t
_g.submit(gr, gr["questions"][0]["answer"], gr["q_start"] + 1); _g.tick(gr, gr["q_start"] + 100)
check("answer + timeouts finish the run", gr["done"])
run("Learning Games"); check("result screen saves the quiz once", any("Result saved" in o for o in OUT) and db.get_student("stu1") is not None and _g.played_count("stu1") == 1, OUT[:8])
run("Learning Games"); check("a rerun does not save it twice", _g.played_count("stu1") == 1)
fake.session_state.pop("game_run", None); OVR.pop("game_n_quick")
OVR["game_play_rapid"] = True; OVR["game_subject_rapid"] = "Mixed"
run("Learning Games"); gr = fake.session_state.get("game_run")
check("starting Rapid Fire creates a 60-second run", bool(gr) and gr["game"] == "rapid" and gr["total"] == 60 and len(gr["questions"]) >= 5, gr and gr["game"])
OVR.pop("game_play_rapid"); fake.session_state.pop("game_run", None)
# the goal dialog: open, edit, save, persist
fut = (_dt.date.today() + _dt.timedelta(days=40))
fake.session_state["_goal_dialog"] = True
OVR.update({"goal_exam": "ECAT", "goal_uni": "NED University", "goal_scale": 400, "goal_score": 320, "goal_date": fut, "goal_save": True})
run("Dashboard")
g2 = db.get_student("stu1"); check("edit goal saves exam, university, score, scale and date", (g2["exam_name"], g2["goal_university"], g2["goal_score"], g2["goal_scale"], g2["exam_date"]) == ("ECAT", "NED University", 320, 400, fut.isoformat()), g2)
for k_ in ("goal_exam", "goal_uni", "goal_scale", "goal_score", "goal_date", "goal_save"): OVR.pop(k_, None)
run("Dashboard"); check("saved goal shows in the sidebar card after rerun", any("ECAT" in o and "NED University" in o for o in OUT), OUT[:6])
fake.session_state["_goal_dialog"] = True
OVR.update({"goal_exam": "MDCAT", "goal_scale": 180, "goal_score": 500, "goal_date": fut, "goal_save": True})
run("Dashboard"); check("invalid score is rejected and nothing changes", db.get_student("stu1")["goal_score"] == 320 and any("target score" in o.lower() for o in OUT), OUT[-6:])
for k_ in ("goal_exam", "goal_scale", "goal_score", "goal_date", "goal_save"): OVR.pop(k_, None)
fake.session_state.pop("_goal_dialog", None)

# ======================================================================== v5.5: Today's Schedule
db.ensure_student("stu_sch", "Sched Kid"); db.save_plan("stu_sch", "MDCAT", "", [{"day": "Day 1", "sessions": [{"subject": "Biology", "topic": "Cell Cycle", "minutes": 20, "activity": "Read notes"}, {"subject": "Chemistry", "topic": "Bonding", "minutes": 15, "activity": "MCQs"}]}])
run("Dashboard", student_id="stu_sch", student_name="Sched Kid")
check("schedule has no section headings (no 'Study plan' / 'Tutor assignments' labels)", not any(o.strip() in ("Study plan", "Tutor assignments & quizzes") or 'class="pp-label">Study plan' in o or "Tutor assignments" in o for o in OUT), [o[:60] for o in OUT if "ssign" in o])
check("each schedule row shows its tab icon", sum(1 for o in OUT if o == ":material/event_note:") >= 2, [o for o in OUT if "material" in o][:4])
OVR["sch_done_0"] = True; run("Dashboard", student_id="stu_sch", student_name="Sched Kid"); OVR.clear()
import dashboard_data as _dd2
check("pressing Done marks the session and saves it", len(_dd2.done_keys("stu_sch", db.progress.local_today())) == 1 and _dd2.schedule("stu_sch")["items"][0]["done"])
keys_seen = []
_orig = FakeSt.button
FakeSt.button = staticmethod(lambda label, key=None, **k: (keys_seen.append(key), _orig(label, key=key, **k))[1])
run("Dashboard", student_id="stu_sch", student_name="Sched Kid"); FakeSt.button = staticmethod(_orig)
check("the finished session's button switches to the green style, the other stays plain", "sch_donex_0" in keys_seen and "sch_done_1" in keys_seen and "sch_done_0" not in keys_seen, [k_ for k_ in keys_seen if k_ and k_.startswith("sch")])
OVR["sch_donex_0"] = True; run("Dashboard", student_id="stu_sch", student_name="Sched Kid"); OVR.clear()
check("pressing a green Done again undoes it", _dd2.done_keys("stu_sch", db.progress.local_today()) == set())
# ======================================================================== v5.6: search, schedule polish, mock tests are not performance
import theme as _styles, time as _time
_css = _styles.build_css("#8B1E3F", "#0E1117", "#FAFAFA") if hasattr(_styles, "build_css") else ""
check("a finished schedule title has no line-through", "text-decoration: line-through" not in _css.split(".pp-sch.done .t")[1].split("}")[0] if ".pp-sch.done .t" in _css else False)
check("sidebar buttons force every inner wrapper to start-align", 'button *, [class*="st-key-navon_"] button * { justify-content: flex-start' in _css)
db.ensure_student("stu_srch", "Search Kid")
db.record_quiz("stu_srch", "Chemistry", "Periodic table", [{"question": "Periodic Q1", "options": {"A": "a", "B": "b"}, "answer": "A", "concept": "c", "explanation": "e", "difficulty": "Medium"}], {0: "B"}, "Medium")
fake.session_state["global_search"] = "periodic"; run("Dashboard", student_id="stu_srch", student_name="Search Kid")
check("typing in the search bar lists matching mistakes and history", any("Mistake" in o and "Periodic table" in o for o in OUT) and any("pp-sr" in o and "History" in o for o in OUT), OUT[-6:])
fake.session_state["global_search"] = "mock"; run("Dashboard", student_id="stu_srch", student_name="Search Kid")
check("searching a page name offers that page", any('<div class="t">Mock Test</div>' in o for o in OUT), OUT[-5:])
OVR["search_open_0"] = True; g56 = run("Dashboard", student_id="stu_srch", student_name="Search Kid"); OVR.clear()
check("Open on a result navigates to that page", fake.session_state.get("nav_page") == "Mock Test", fake.session_state.get("nav_page"))
fake.session_state["global_search"] = ""; run("Dashboard", student_id="stu_srch", student_name="Search Kid")
fake.session_state["global_search"] = "mock"; OVR["search_open_0"] = True; run("Dashboard", student_id="stu_srch", student_name="Search Kid"); OVR.clear()
check("opening a result also empties the search box", fake.session_state.get("global_search") == "")
run("Dashboard", student_id="stu_srch", student_name="Search Kid")
check("an empty search shows no result panel", not any('class="pp-sr' in o for o in OUT))
# a submitted mock test is saved but not counted
db.ensure_student("stu_mk", "Mock Kid")
_mq = [{"question": f"MockQ{i}", "options": {"A": "a", "B": "b"}, "answer": "A", "concept": "c", "explanation": "e", "difficulty": "Medium", "subject": "Biology", "topic": "Cells", "section": "Biology"} for i in range(3)]
_mock_quiz = {"uid": "mkuid1", "questions": _mq, "subject": "Mock Test", "topic": "Quick mock", "difficulty": "Mixed", "sources": [], "time_limit_sec": 600, "started_at": _time.time(), "finished": False,
              "answers": {0: "B", 1: "B", 2: "B"}, "answer_ts": {0: _time.time(), 1: _time.time(), 2: _time.time()}, "result": None, "negative": False, "blueprint": "Quick mock", "mock": True}
OVR["mk_submit_mkuid1"] = True; run("Mock Test", student_id="stu_mk", student_name="Mock Kid", mock=_mock_quiz); OVR.clear()
check("a submitted mock test is saved but adds nothing to performance", db.dashboard_stats("stu_mk")["attempted"] == 0 and len(db.history("stu_mk")) == 0 and len(__import__("mock").history("stu_mk")) == 1,
      (db.dashboard_stats("stu_mk")["attempted"], len(__import__("mock").history("stu_mk"))))
# ======================================================================== v5.7: one open mistake must not crash Today (slider min == max)
db.ensure_student("stu_one", "One Mistake")
db.record_quiz("stu_one", "Physics", "Motion", [{"question": "Only one wrong", "options": {"A": "a", "B": "b"}, "answer": "A", "concept": "c", "explanation": "e", "difficulty": "Medium"}], {0: "B"}, "Medium")
try:
    run("Today", student_id="stu_one", student_name="One Mistake"); ok_one = True
except Exception as e_:
    ok_one = False; print("ERR", e_)
check("Today opens with exactly one open mistake (no slider error)", ok_one and any("Retake" in o or "retake" in o.lower() for o in OUT), OUT[:5])
# ======================================================================== v5.8: new logo and name, no line through finished Finish Line tasks
check("no finished item anywhere is struck through (Finish Line and schedule)", "line-through" not in _css)
import login_ui as _lu, ui_kit as _uk
check("the brand is Prep.AI everywhere the user sees it", _lu.BRAND_NAME == "Prep.AI" and "Prep<em>.AI</em>" in _uk.brand() and "Prep AI" not in _uk.brand() and "Prep AI" not in _lu.brand_row())
from PIL import Image as _Im
check("logo assets are the new transparent PNGs", all(_Im.open(ROOT / "assets" / f).mode == "RGBA" for f in ("logo_icon.png", "logo_icon_256.png", "logo_full.png", "favicon.png")) and _Im.open(ROOT / "assets" / "play_store_icon_512.png").size == (512, 512))
# ======================================================================== v5.4
import diary as _diary, career_profile as _cp, dashboard_data as _dd
import agent_system as _as
_as.Orchestrator.tutor_request = lambda self, ctx: "LESSON TEXT"
# ---- Mistakes Diary: badge, Teach me, moving on removes the mistake and lowers the count
D = "stu_diary"; db.ensure_student(D, "Diary Kid")
QD = [{"question": f"DiaryQ{i}", "options": {"A": "a", "B": "b"}, "answer": "A", "concept": "c", "explanation": f"because {i}", "difficulty": "Medium"} for i in range(3)]
db.record_quiz(D, "Biology", "Cells", QD, {0: "B", 1: "B", 2: "B"}, "Medium")
run("Mistakes Diary", student_id=D, student_name="Diary Kid")
check("diary shows 3 mistakes and the red sidebar badge", "METRIC Mistakes to review=3" in OUT and any('content: "3"' in o for o in OUT), OUT[:12])
check("every mistake has a Teach me button", sum(1 for o in OUT if "DiaryQ" in o) >= 3)
ids = [m["id"] for m in _diary.open_mistakes(D)]
OVR[f"diary_teach_{ids[0]}"] = True; run("Mistakes Diary", student_id=D, student_name="Diary Kid"); OVR.clear()
run("Mistakes Diary", student_id=D, student_name="Diary Kid")
check("teaching shows the lesson but keeps the mistake until you move on", any("LESSON TEXT" in o for o in OUT) and _diary.open_count(D) == 3, OUT[:10])
OVR[f"diary_teach_{ids[1]}"] = True; run("Mistakes Diary", student_id=D, student_name="Diary Kid"); OVR.clear()
run("Mistakes Diary", student_id=D, student_name="Diary Kid")
check("moving to the next mistake removes the previous one and the badge drops to 2", _diary.open_count(D) == 2 and ids[0] not in [m["id"] for m in _diary.open_mistakes(D)] and any('content: "2"' in o for o in OUT), OUT[:12])
OVR["diary_next"] = True; run("Mistakes Diary", student_id=D, student_name="Diary Kid"); OVR.clear()
check("Next mistake removes the one just taught", _diary.open_count(D) == 1, _diary.open_count(D))
run("Mistakes Diary", student_id=D, student_name="Diary Kid"); check("badge shows the remaining 1", any('content: "1"' in o for o in OUT))
# ---- Study plan: calendar from the saved plan
db.ensure_student("stu_plan", "Planner")
db.save_plan("stu_plan", "MDCAT", (_dt.date.today() + _dt.timedelta(days=9)).isoformat(),
             [{"day": "Day 1", "sessions": [{"subject": "Biology", "topic": "Cell cycle", "minutes": 60, "activity": "Read notes", "source": "Biology.pdf p.12"}, {"subject": "Chemistry", "topic": "Bonding", "minutes": 45, "activity": "Practice MCQs"}]},
              {"day": "Day 2", "sessions": [{"subject": "Physics", "topic": "Optics", "minutes": 90, "activity": "Revision"}]}])
run("Study Plan", student_id="stu_plan", student_name="Planner")
check("study plan is drawn as a calendar with times and a download", any("pp-cal" in o and "Cell cycle" in o and "17:00" in o for o in OUT) and any("DOWNLOAD Add to my calendar" in o for o in OUT), [o[:80] for o in OUT[:8]])
# ---- Path Finder wizard: nine steps, saved after each, recommendation at the end
P = "stu_path"; db.ensure_student(P, "Path Kid")
run("Path Finder", student_id=P, student_name="Path Kid")
check("path finder opens on step 1 of 9", any("Step 1 of 9" in o and "Academic background" in o for o in OUT), OUT[:5])
OVR.update({"cp0_stream": "Pre-Medical", "cp0_fsc_pct": 82.0, "cp0_matric_pct": 90.0, "cp1_interests": ["Medicine & healthcare"], "cp1_degree1": "MBBS", "cp1_degree2": "Pharm-D",
            "cp4_universities": "KMU\nUHS", "cp4_family_income": 40000.0, "cp5_backup": "Pharm-D at a public university", "Save and continue": True})
for want in range(2, 9):
    run("Path Finder", student_id=P, student_name="Path Kid")
    check(f"Save and continue moves to step {want}", fake.session_state.get("cp_step") == want - 1, fake.session_state.get("cp_step"))
saved, step = _cp.load(P)
check("answers are saved after each step and the student resumes where they stopped", saved.get("stream") == "Pre-Medical" and saved.get("degree1") == "MBBS" and step >= 7, (saved.keys(), step))
check("family income is never stored", "family_income" not in saved)
fake.session_state["cp_step"] = 8; OVR.pop("Save and continue"); OVR.update({"Find my path": True, "cp_web": False, "cp_docs": False, "cp_sig": False})
run("Path Finder", student_id=P, student_name="Path Kid"); OVR.clear()
st_ = fake.session_state.get("pf_state")
check("Find my path runs the pipeline and keeps the wizard data", bool(st_) and st_["profile"]["stream"] == "Pre-Medical" and st_["data"].get("degree1") == "MBBS", st_ and st_["profile"])
run("Path Finder", student_id=P, student_name="Path Kid"); check("recommendation card appears after the run", any("My recommendation" in o for o in OUT) or any("3 degree options" in o for o in OUT), OUT[:10])
for key in ("cp_data", "cp_step", "pf_state"): fake.session_state.pop(key, None)
# ---- tutor Settings
run("Settings", is_tutor=True, student_id=TUTOR_ID, student_name="Tutor"); check("tutor Settings page opens", any("Tutor Settings" in o for o in OUT), OUT[:5])
OVR.update({"Save settings": True, "Difficulty": "Hard", "Number of MCQs": 30, "Time limit (minutes, 0 = none)": 15})
run("Settings", is_tutor=True, student_id=TUTOR_ID, student_name="Tutor"); OVR.clear()
tp = db.get_preferences(TUTOR_ID)
check("tutor quiz defaults are saved", (tp.get("tutor_difficulty"), tp.get("tutor_count"), tp.get("tutor_minutes")) == ("Hard", 30, 15), tp)
run("Tutor Dashboard", is_tutor=True, student_id=TUTOR_ID, student_name="Tutor"); check("Create Quiz still renders with the defaults", True)
fake.session_state["is_tutor"] = False

print("\nFAILED:" if failures else "\nALL PASSED", failures or "")
sys.exit(1 if failures else 0)
