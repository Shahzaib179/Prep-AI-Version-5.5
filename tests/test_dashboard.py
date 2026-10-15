"""Dashboard data (checklist, schedule, subject performance), the score estimate and the HTML building blocks."""
import json, pathlib, sys, tempfile, types, unittest
from datetime import date, datetime, timedelta
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
class _St(types.ModuleType):
    session_state = {}; secrets = {}
    def __getattr__(self, n):
        if n.startswith("__"): raise AttributeError(n)
        return lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda f: f))
sys.modules["streamlit"] = _St("streamlit")
for name in ("groq", "ddgs", "faiss", "sentence_transformers"):
    m = types.ModuleType(name); m.Groq = object; m.DDGS = object; m.SentenceTransformer = object; sys.modules[name] = m
import config; config.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "d.db"
import db, db_core, navigation, progress, score_estimate as se, ui_kit as k, dashboard_data as dd, theme, styles  # noqa: E402
db.init_db()
n = [0]
def sid():
    n[0] += 1; s = f"dash{n[0]}"; db.ensure_student(s, s); return s
def Q(i, ok="A"): return {"question": f"Dash question number {i}?", "options": {"A": "a", "B": "b", "C": "c", "D": "d"}, "answer": ok, "concept": f"c{i}", "explanation": "e", "difficulty": "Medium"}
def plan(days=3): return [{"day": f"Day {i}", "sessions": [{"subject": "Biology", "topic": f"Genetics part {i}", "minutes": 30, "activity": "Read", "source": ""}, {"subject": "Chemistry", "topic": "Acids", "minutes": 20, "activity": "MCQs"}]} for i in range(1, days + 1)]

class FinishLine(unittest.TestCase):
    def test_exactly_four_items_in_fixed_order(self):
        s = sid(); t = dd.finish_line_tasks(s)
        self.assertEqual([x["key"] for x in t], ["goal", "revision", "mistakes", "daily"]); self.assertTrue(all(x["kind"] == "auto" for x in t))
        self.assertEqual([x["done"] for x in t], [False, True, True, False])          # nothing due / open counts as complete; the rest still to do
        db.save_plan(s, "MDCAT", "", plan(1))
        self.assertEqual(len(dd.finish_line_tasks(s)), 4)                                # study-plan sessions are not part of the finish line
    def test_plan_sessions_have_keys_for_the_schedule(self):
        s = sid(); db.save_plan(s, "MDCAT", "", plan(2)); sch = dd.schedule(s)
        self.assertTrue(sch["sessions"] and all(x["key"].startswith("plan:") for x in sch["sessions"]))

class ScheduleItems(unittest.TestCase):
    def test_one_list_with_tab_icons_and_done_only_on_study_plan(self):
        import classes as cl
        s = sid(); tut = "tut_" + s; db.ensure_student(tut, "Tutor"); db.set_role(tut, "tutor"); db.save_plan(s, "MDCAT", "", plan(2))
        c = cl.create_class(tut, "Bio class"); cl.join_class(s, c["join_code"]); code = db.create_shared_quiz(tut, "Cells quiz", "Biology", "Cells", "Medium", [Q(1)])
        ok, _ = cl.create_assignment(tut, c["id"], code, "Cells quiz", (datetime.utcnow() + timedelta(days=2)).isoformat(timespec="minutes")); self.assertTrue(ok)
        items = dd.schedule(s)["items"]
        self.assertEqual([i["kind"] for i in items], ["plan", "plan", "quiz"])                                   # study plan first, then tutor work
        self.assertEqual([i["route"] for i in items], ["Study Plan", "Study Plan", "My Classes"])
        self.assertEqual([i["icon"] for i in items], [dd.tab_icon("Study Plan")] * 2 + [dd.tab_icon("My Classes")])
        self.assertEqual([i["can_done"] for i in items], [True, True, False]); self.assertEqual(len({i["key"] for i in items}), 3)
        self.assertIn("Cells quiz", items[2]["title"]); self.assertIn("Bio class", items[2]["detail"]); self.assertTrue(items[2]["due_at"])
    def test_every_icon_is_a_real_sidebar_icon_and_unknown_route_has_a_fallback(self):
        for route, icon in dd.ROUTE_ICON.items(): self.assertTrue(icon)
        self.assertEqual(dd.tab_icon("Study Plan"), "event_note"); self.assertEqual(dd.tab_icon("Nope"), "event")
    def test_done_state_follows_the_ticks(self):
        s = sid(); db.save_plan(s, "MDCAT", "", plan(1)); today = progress.local_today(); first = dd.schedule(s, today)["items"][0]
        self.assertFalse(first["done"]); dd.set_task_done(s, today, first["key"], True)
        self.assertEqual([i["done"] for i in dd.schedule(s, today)["items"]], [True, False])
    def test_nothing_scheduled_gives_no_items(self):
        self.assertEqual(dd.schedule(sid())["items"], [])

class Estimate(unittest.TestCase):
    def test_not_ready_until_enough_answers(self):
        r = se.estimate(5, 4); self.assertFalse(r["ready"]); self.assertEqual(r["needed"], config.SCORE_MIN_ANSWERS - 5); self.assertNotIn("score", r)
    def test_ready_scales_to_180_with_a_range(self):
        r = se.estimate(40, 30); self.assertTrue(r["ready"]); self.assertEqual((r["scale"], r["score"], r["accuracy"]), (180, 135, 75.0))
        self.assertTrue(r["low"] < r["score"] < r["high"] <= 180)
        wide, narrow = se.estimate(20, 15), se.estimate(400, 300); self.assertGreater(wide["high"] - wide["low"], narrow["high"] - narrow["low"])
    def test_edges(self):
        self.assertEqual(se.estimate(20, 20)["score"], 180); self.assertEqual(se.estimate(20, 0)["score"], 0); self.assertEqual(se.estimate(20, 99)["score"], 180)
        self.assertEqual(se.estimate(-5, 3)["answered"], 0)

class Blocks(unittest.TestCase):
    def test_everything_is_escaped(self):
        evil = '<script>alert(1)</script>'
        for html in (k.greeting(evil, evil), k.topbar(evil, evil, [evil], evil), k.badge(evil), k.empty(evil), k.row(evil, evil, ""), k.task_row(evil, evil, True), k.qcard(1, evil), k.finish_line(1, 2, evil, evil), k.sidebar_goal(evil, evil, evil), k.ring(50, evil)):
            self.assertNotIn("<script>", html)
    def test_no_data_is_never_drawn_as_zero(self):
        self.assertIn("–", k.ring(None, "BIO")); self.assertNotIn("0%", k.ring(None, "BIO")); self.assertIn("40%", k.ring(40, "BIO"))
        g = k.gauge(None, 180); self.assertIn("–", g); self.assertNotIn("<line", g)            # empty dial, no needle
        g = k.gauge(135, 180, 120, 150); self.assertIn("135", g); self.assertIn("<line", g)
    def test_finish_line_progress(self):
        self.assertIn("2/4 done", k.finish_line(2, 4, "T", "l")); self.assertIn("width:50.0%", k.finish_line(2, 4, "T", "l")); self.assertIn("0/0 done", k.finish_line(0, 0, "T", "l"))
    def test_qnav_marks_answered(self):
        h = k.qnav(3, {1}); self.assertEqual(h.count('class="on"'), 1); self.assertIn('href="#q3"', h)

class Tokens(unittest.TestCase):
    def test_default_and_custom_palettes(self):
        css = theme.build_css("#92002D"); self.assertIn("--p-primary: #92002D", css); self.assertIn("#F8F3F5", css); self.assertNotIn("user theme", css)
        dark = theme.build_css("#92002D", "#0E1117", "#F3F4F6"); self.assertIn("user theme", dark); self.assertIn("--p-bg: #0E1117", dark)
    def test_text_is_readable_on_cards_in_every_preset(self):
        for name, pair in list(config.THEME_PRESETS.items()) + [("Default", (theme.BRAND_BG, theme.BRAND_TEXT))]:
            if not pair: continue
            t = theme.tokens("#92002D", *pair); card = t.split("--p-card: ")[1][:7]; text = t.split("--p-text: ")[1][:7]; muted = t.split("--p-muted: ")[1][:7]
            self.assertGreaterEqual(theme.contrast_ratio(card, text), 7, name); self.assertGreaterEqual(theme.contrast_ratio(card, muted), 3.4, name)
        self.assertGreaterEqual(theme.contrast_ratio("#FFFFFF", "#92002D"), 7)         # white text on the brand colour
    def test_css_only_uses_defined_variables(self):
        import re
        css = theme.build_css("#92002D"); used = set(re.findall(r"var\((--[a-z0-9-]+)\)", css)); defined = set(re.findall(r"(--[a-z0-9-]+):", css))
        self.assertEqual(used - defined, set())
        self.assertEqual(css.count("{"), css.count("}"))
        self.assertIn("@media (max-width: 900px)", css)

class Nav(unittest.TestCase):
    def test_resolve_and_groups(self):
        self.assertEqual(navigation.resolve("My Classes (3)", False), "My Classes"); self.assertEqual(navigation.resolve("Tutor Dashboard", False), "Dashboard")
        self.assertEqual(navigation.resolve("Dashboard", True), "Tutor Dashboard"); self.assertEqual(navigation.resolve(None, True), "Tutor Dashboard"); self.assertEqual(navigation.resolve("nonsense", False), "Dashboard")
        r = navigation.routes(False); self.assertEqual(len(r), len(set(r))); self.assertEqual(navigation.label("My Classes", 2), "My Classes (2)"); self.assertEqual(navigation.label("Today", 2), "Today")

class Data(unittest.TestCase):
    def test_new_student_checklist_has_only_real_items(self):
        s = sid(); t = dd.todays_tasks(s); keys = [x["key"] for x in t]
        self.assertIn("goal", keys); self.assertIn("daily", keys); self.assertFalse(any(x["kind"] == "plan" for x in t)); self.assertEqual(dd.task_progress(t)[0], 0)
        sch = dd.schedule(s); self.assertEqual(sch["sessions"], []); self.assertIsNone(sch["plan"])
    def test_plan_sessions_become_tickable_tasks_and_persist(self):
        s, other = sid(), sid(); db.save_plan(s, "MDCAT", "2026-12-01", plan()); today = progress.local_today()
        t = dd.todays_tasks(s, today); pt = [x for x in t if x["kind"] == "plan"]; self.assertEqual(len(pt), 2); self.assertIn("Genetics part 1", pt[0]["title"])
        dd.set_task_done(s, today, pt[0]["key"], True); dd.set_task_done(s, today, pt[0]["key"], True)              # idempotent
        t = dd.todays_tasks(s, today); self.assertEqual(sum(1 for x in t if x["done"]), 1); self.assertEqual(dd.done_keys(other, today), set())
        self.assertEqual([x["done"] for x in dd.schedule(s, today)["sessions"]], [True, False])
        dd.set_task_done(s, today, pt[0]["key"], False); self.assertEqual(dd.done_keys(s, today), set())
        self.assertEqual(dd.todays_tasks(s, today + timedelta(days=1))[-2]["key"].split(":")[2], "2")            # tomorrow is Day 2 of the plan
    def test_plan_end_and_malformed_plans(self):
        s = sid(); db.save_plan(s, "E", "", plan(2)); today = progress.local_today()
        late = dd.plan_today(s, today + timedelta(days=5)); self.assertTrue(late["ended"]); self.assertEqual(late["sessions"], [])
        t = sid(); db.save_plan(t, "E", "", [{"day": "D", "sessions": ["junk", {"topic": "ok", "minutes": 5}]}, "junk"])
        self.assertEqual(len([x for x in dd.todays_tasks(t) if x["kind"] == "plan"]), 1)
        u = sid(); db.save_plan(u, "E", "", {"not": "a list"}); self.assertIsNone(dd.plan_today(u))
    def test_subject_performance_is_honest(self):
        s = sid(); perf = dd.subject_performance(s)
        self.assertEqual([p["subject"] for p in perf], list(dd.STANDARD_SUBJECTS)); self.assertTrue(all(not p["has_data"] for p in perf))
        qs = [Q(i) for i in range(6)]; db.record_quiz(s, "Biology", "Cells", qs, {i: "A" for i in range(6)}, "Medium")
        perf = {p["subject"]: p for p in dd.subject_performance(s)}; self.assertTrue(perf["Biology"]["has_data"]); self.assertEqual(perf["Biology"]["attempts"], 6)
        self.assertGreater(perf["Biology"]["mastery"], 50); self.assertFalse(perf["Physics"]["has_data"])
        self.assertEqual(len(dd.recent_quizzes(s)), 1)
    def test_days_to_exam(self):
        t = date(2026, 10, 1); self.assertEqual(dd.days_to_exam("2026-10-11", t), 10); self.assertIsNone(dd.days_to_exam("2026-09-01", t)); self.assertIsNone(dd.days_to_exam("", t)); self.assertIsNone(dd.days_to_exam("bad", t))
    def test_migration_creates_table_and_recolours(self):
        with db.connect() as con: con.execute("SELECT COUNT(*) FROM daily_tasks").fetchone()
        s = sid(); self.assertEqual(db.get_preferences(s)["ui_color"], "Burgundy")

if __name__ == "__main__": unittest.main()
