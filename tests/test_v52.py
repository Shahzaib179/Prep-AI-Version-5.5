"""v5.2: editable goal, learning games, leaderboard, score trend, logo assets, sidebar HTML."""
import pathlib, sys, tempfile, types, unittest
from datetime import date, timedelta
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
import config; config.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "v52.db"
import db, goals, games, leaderboard, migrations, navigation, progress, score_estimate as se, ui_kit as k, styles  # noqa: E402
db.init_db()
n = [0]
def sid(name="Student"):
    n[0] += 1; s = f"v52_{n[0]}"; db.ensure_student(s, name); return s
TODAY = progress.local_today()

class Goal(unittest.TestCase):
    def test_migration_adds_columns_and_table(self):
        self.assertGreaterEqual(migrations.current_version(), 13)
        s = sid(); st = db.get_student(s)
        for c in ("goal_university", "goal_score", "goal_scale"): self.assertIn(c, st)
    def test_validate(self):
        ok, e = goals.validate("MDCAT", " UHS  Lahore ", 150, 180, TODAY + timedelta(days=30)); self.assertEqual(e, []); self.assertEqual(ok["goal_university"], "UHS Lahore")
        for args in (("", "", 10, 180, TODAY), ("MDCAT", "", 200, 180, TODAY), ("MDCAT", "", -1, 180, TODAY), ("MDCAT", "", 10, 0, TODAY), ("MDCAT", "", 10, 5000, TODAY),
                     ("MDCAT", "", 10, 180, TODAY - timedelta(days=1)), ("MDCAT", "", 10, 180, None), ("MDCAT", "", "abc", 180, TODAY)):
            self.assertIsNone(goals.validate(*args)[0], args)
        self.assertIsNone(goals.validate("MDCAT", "", 0, 180, TODAY)[0]["goal_score"])      # 0 = no target
    def test_save_persists_and_keeps_other_data(self):
        s = sid("Keeper"); db.update_student(s, daily_minutes=95)
        clean, _ = goals.validate("ECAT", "NED", 300, 400, TODAY + timedelta(days=9)); goals.save_goal(s, clean)
        g = goals.get_goal(db.get_student(s)); self.assertEqual((g["exam"], g["university"], g["score"], g["scale"], g["days"]), ("ECAT", "NED", 300, 400, 9))
        self.assertEqual(db.get_student(s)["daily_minutes"], 95); self.assertEqual(db.get_student(s)["name"], "Keeper")
    def test_unset_goal(self):
        g = goals.get_goal(db.get_student(sid())); self.assertFalse(g["is_set"]); self.assertEqual(g["scale"], config.SCORE_SCALE)
    def test_describe(self):
        self.assertEqual(goals.describe({"exam": "MDCAT", "university": "UHS", "days": 1, "score": 150, "scale": 180}), ("MDCAT · UHS", "1 day to go · target 150/180"))

def quiz(n=10):
    return [{"question": f"Game question {i}?", "options": {"A": "a", "B": "b", "C": "c", "D": "d"}, "answer": "A", "concept": "c", "explanation": "e", "difficulty": "Medium"} for i in range(n)]

class Games(unittest.TestCase):
    def test_questions_are_real_and_distinct(self):
        s = sid()
        for subj in ("Biology", "Mixed"):
            qs = games.build_questions(s, subj, 10, seed=1)
            self.assertGreaterEqual(len(qs), 5)
            self.assertEqual(len({progress.qhash(q["question"]) for q in qs}), len(qs))
            import daily, question_tools as qt
            gold = {progress.qhash(g["question"]) for g in daily._golden()}
            self.assertTrue(all(progress.qhash(q["question"]) in gold for q in qs))        # nothing invented
            self.assertTrue(all(not qt.validate_question(qt.normalize_question(q)) for q in qs))
    def test_result_stored_once(self):
        s = sid(); self.assertTrue(games.record_result(s, "quick", "Biology", 7, 10, 120, 555)); self.assertFalse(games.record_result(s, "quick", "Biology", 7, 10, 120, 555))
        games.record_result(s, "quick", "Biology", 9, 10, 200, 556); games.record_result(s, "quick", "Biology", 9, 10, 100, 557)
        b = games.best(s)["quick"]; self.assertEqual((b["correct"], b["taken_sec"]), (9, 100)); self.assertEqual(games.played_count(s), 3)
    def test_rapid_best_is_most_correct(self):
        s = sid(); games.record_result(s, "rapid", "Mixed", 5, 5, 60, 1); games.record_result(s, "rapid", "Mixed", 9, 14, 60, 2)
        self.assertEqual(games.best(s)["rapid"]["correct"], 9)
    def test_generate_failure_never_blocks(self):
        def boom(*a): raise RuntimeError("ai down")
        self.assertGreaterEqual(len(games.build_questions(sid(), "Physics", 10, boom, seed=2)), 5)
    def test_legacy_title(self):
        self.assertEqual(games.title_of("sprint"), "Subject Sprint (retired)"); self.assertEqual(games.title_of("rapid"), "Rapid Fire")

def Qs(n): return [{"question": f"Q{i}", "options": {"A": "a", "B": "b"}, "answer": "A"} for i in range(n)]

class Engine(unittest.TestCase):
    def test_quick_ten_seconds_each(self):
        r = games.new_run("quick", Qs(3), "Biology", 100.0)
        self.assertEqual(games.deadline(r), 110.0); self.assertAlmostEqual(games.remaining(r, 104), 6.0)
        self.assertTrue(games.submit(r, "A", 103.0)); self.assertEqual((r["idx"], r["q_start"]), (1, 103.0))     # next question gets its own 10 s
        self.assertFalse(games.tick(r, 112.9)); self.assertEqual(r["idx"], 1)
        self.assertFalse(games.tick(r, 113.5)); self.assertEqual((r["idx"], r["answers"][1]), (2, None))          # timed out: skipped, next question shown
        self.assertTrue(games.tick(r, 134.0)); self.assertTrue(r["done"])
        o = games.outcome(r); self.assertEqual((o["total"], o["answered"], o["correct"], o["limit"]), (3, 1, 1, 30))
    def test_quick_late_answer_rejected_but_grace_allowed(self):
        r = games.new_run("quick", Qs(3), "Biology", 0.0)
        self.assertTrue(games.submit(r, "A", 10.5))                   # inside the 0.8 s network grace
        self.assertFalse(games.submit(r, "A", 10.5 + 10.9))           # too late: counted as skipped
        self.assertEqual(r["answers"][1], None)
    def test_quick_catches_up_after_away(self):
        r = games.new_run("quick", Qs(4), "Biology", 0.0); games.tick(r, 21.0)
        self.assertEqual(r["idx"], 2); games.tick(r, 100.0); self.assertTrue(r["done"]); self.assertEqual(games.outcome(r)["answered"], 0)
    def test_quick_all_answered_finishes(self):
        r = games.new_run("quick", Qs(2), "Biology", 0.0); games.submit(r, "B", 1); games.submit(r, "A", 2)
        self.assertTrue(r["done"]); o = games.outcome(r); self.assertEqual((o["correct"], o["answered"], o["total"]), (1, 2, 2))
    def test_rapid_sixty_seconds(self):
        r = games.new_run("rapid", Qs(30), "Mixed", 1000.0)
        for t in (1001, 1002, 1003): games.submit(r, "A", t)
        self.assertEqual(r["idx"], 3); self.assertFalse(r["done"]); self.assertEqual(games.deadline(r), 1060.0)
        games.tick(r, 1060.0); self.assertTrue(r["done"])
        self.assertFalse(games.submit(r, "A", 1061)); o = games.outcome(r)
        self.assertEqual((o["total"], o["answered"], o["correct"], o["taken"]), (3, 3, 3, 60))     # the unanswered 4th question is not recorded
    def test_rapid_late_answer_not_counted_and_pool_exhaustion(self):
        r = games.new_run("rapid", Qs(30), "Mixed", 0.0); self.assertFalse(games.submit(r, "A", 61.0)); self.assertTrue(r["done"]); self.assertEqual(games.outcome(r)["answered"], 0)
        r = games.new_run("rapid", Qs(2), "Mixed", 0.0); games.submit(r, "A", 1); games.submit(r, "B", 2)
        self.assertTrue(r["done"] and r["exhausted"]); o = games.outcome(r); self.assertEqual((o["answered"], o["correct"], o["timed_out"]), (2, 1, False))
    def test_quit_ends_round(self):
        r = games.new_run("rapid", Qs(5), "Mixed", 0.0); games.submit(r, "A", 3); games.abort(r, 4); self.assertEqual(games.outcome(r)["taken"], 4)

class GameIsNotPerformance(unittest.TestCase):
    def _round(self, s, wrong=3):
        qs = [{"question": f"Game question {i} {s}", "options": {"A": "x", "B": "y"}, "answer": "A", "explanation": "e", "subject": "Biology", "topic": "t"} for i in range(6)]
        return db.record_game_round(s, "Biology", qs, {i: ("B" if i < wrong else "A") for i in range(6)})
    def test_wrong_game_answers_never_reach_performance(self):
        import diary
        s = sid(); out = self._round(s)
        self.assertEqual((out["answered"], out["correct"]), (6, 3)); self.assertGreater(out["xp"], 0)
        self.assertEqual(diary.open_count(s), 0); self.assertEqual(db.recent_mistakes(s), []); self.assertEqual(progress.retakeable_mistakes(s), [])
        import db_core
        with db_core.connect() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM quiz_attempts WHERE student_id=?", (s,)).fetchone()[0], 0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM question_attempts WHERE student_id=?", (s,)).fetchone()[0], 0)
        self.assertEqual(db.topic_mastery(s), [])
    def test_game_still_earns_xp_and_streak(self):
        s = sid(); self._round(s); p = progress.get_progress(s)
        self.assertEqual(p["today_questions"], 6); self.assertGreaterEqual(p["streak"], 1); self.assertGreater(p["total_xp"], 0)
    def test_migration_removes_old_game_mistakes(self):
        import db_core, migrations
        s = sid(); play(s, 5, 10)                                      # a normal quiz: 5 mistakes must stay
        qid = db.record_quiz(s, "Biology", "Quick MCQ Challenge", quiz(4), {0: "B", 1: "B", 2: "A", 3: "A"}, "Mixed")
        games.record_result(s, "quick", "Biology", 2, 4, 40, qid)
        with db_core.connect() as con:
            before = con.execute("SELECT COUNT(*) FROM mistakes WHERE student_id=?", (s,)).fetchone()[0]
            migrations._m014_diary_career(con)
            after = con.execute("SELECT COUNT(*) FROM mistakes WHERE student_id=?", (s,)).fetchone()[0]
        self.assertEqual((before, after), (7, 5))

def play(s, correct, total=10):
    db.record_quiz(s, "Biology", "t", quiz(total), {i: ("A" if i < correct else "B") for i in range(total)}, "Medium")

class Board(unittest.TestCase):
    def test_privacy_names(self):
        self.assertEqual(leaderboard.display_name("Ayesha Khan Malik", "x"), "Ayesha M.")
        self.assertEqual(leaderboard.display_name("Ali", "x"), "Ali")
        for bad in ("me@gmail.com", "03001234567", "", None, "!!!"): self.assertTrue(leaderboard.display_name(bad, "id1").startswith("Student "), bad)
    def test_ranking_points_ties_and_no_double_count(self):
        a, b, c = sid("Zed Alpha"), sid("Amy Beta"), sid("me@x.com")
        play(a, 10); play(b, 5); play(c, 10)
        for _ in range(2): rows = {r["student_id"]: r for r in leaderboard.ranking("all")}
        self.assertEqual(rows[a]["points"], progress.xp_for(10, 10, True, True))              # exactly the XP ledger, once
        self.assertEqual(rows[b]["points"], progress.xp_for(10, 5, True, False))
        order = [r["student_id"] for r in leaderboard.ranking("all") if r["student_id"] in (a, b, c)]
        self.assertEqual(order, [a, c, b]); self.assertEqual(order, [r["student_id"] for r in leaderboard.ranking("all") if r["student_id"] in (a, b, c)])   # tie a/c: earlier sign-up first, stable
        self.assertEqual(rows[c]["name"][:8], "Student ")
        v = leaderboard.view(b, "all", 1); self.assertTrue(v["me"]["rank"] >= 2 and v["me"]["is_me"]); self.assertNotIn("student_id", v["rows"][0])
        self.assertTrue(all("@" not in r["name"] for r in v["rows"]))
    def test_week_excludes_old(self):
        s = sid("Old Timer"); import db_core
        with db_core.connect() as con: con.execute("INSERT INTO daily_activity(student_id,day,questions,correct,quizzes,xp) VALUES(?,?,?,?,?,?)", (s, (TODAY - timedelta(days=20)).isoformat(), 10, 10, 1, 99))
        self.assertNotIn(s, [r["student_id"] for r in leaderboard.ranking("week")]); self.assertIn(s, [r["student_id"] for r in leaderboard.ranking("all")])
    def test_empty_student_not_listed(self):
        s = sid(); self.assertNotIn(s, [r["student_id"] for r in leaderboard.ranking("all")]); self.assertIsNone(leaderboard.view(s, "all")["me"])

class Predictor(unittest.TestCase):
    def test_trend_waits_for_enough_answers(self):
        rows = [("2026-01-01", 10, 5), ("2026-01-02", 10, 8), ("2026-01-03", 20, 20)]
        t = se.trend(rows, 180)
        self.assertEqual([d for d, _ in t], ["2026-01-02", "2026-01-03"]); self.assertEqual(t[0][1], 117.0); self.assertEqual(t[1][1], round(180 * 33 / 40, 1)); self.assertEqual(se.trend([("d", 5, 5)]), [])
    def test_scale_follows_goal(self):
        self.assertEqual(se.estimate(40, 30, scale=400)["score"], 300)
    def test_recommendations_honest(self):
        self.assertEqual(len(se.recommendations(se.estimate(3, 1), 150, [], 0, 0, 20)), 1)
        tips = se.recommendations(se.estimate(40, 20), 150, [{"subject": "Biology", "topic": "Genetics", "mastery_score": 40}], 2, 5, 20); self.assertTrue(any("Genetics" in t for t in tips)); self.assertTrue(any("accuracy" in t for t in tips))

class Html(unittest.TestCase):
    def test_escaped_and_structure(self):
        evil = "<script>x</script>"
        for h in (k.sidebar_goal(evil, evil, evil, 50), k.bar_row(evil, evil, 50, evil), k.score_vs_target(10, 20, 180), k.leaderboard_rows([{"rank": 1, "name": evil, "points": 5, "correct": 1, "quizzes": 1}])): self.assertNotIn("<script>", h)
        self.assertIn("not set", k.score_vs_target(10, None, 180).lower())
        self.assertIn("points to go", k.score_vs_target(100, 120, 180))
        self.assertIn("polyline", k.trend_svg([("2026-01-01", 50), ("2026-01-02", 60)], 180, 150))
    def test_goal_card_is_flow_layout(self):
        css = styles.COMPONENT_CSS; blk = css[css.index(".pp-goal {"):css.index(".pp-goal {") + 400]
        for bad in ("position: absolute", "position:absolute", "margin-bottom: -"): self.assertNotIn(bad, blk)
        self.assertIn("flow-root", blk)
    def test_assets_and_brand(self):
        for f in ("logo_full.png", "logo_icon.png", "logo_icon_256.png", "favicon.png", "prep_ai_logo_original.png"): self.assertTrue((ROOT / "assets" / f).exists(), f)
        self.assertTrue(k.logo_uri().startswith("data:image/png;base64,")); self.assertIn("<img", k.brand()); self.assertIn("<img", k.login_logo())
    def test_nav(self):
        r = navigation.routes(False)
        for p in ("Learning Games", "Leaderboard", "Score Predictor", "Dashboard", "Settings"): self.assertIn(p, r)
        self.assertEqual(len(r), len(set(r))); self.assertEqual([g for g, _ in navigation.STUDENT_NAV], ["Main", "Learning", "Gamification", "Performance", "Study tools", "Other"])
        import re; src = (ROOT / "app.py").read_text(); keys = set(re.findall(r'^    "([A-Za-z ]+)":', src[src.index("routes = {"):], re.M))
        self.assertTrue(set(r) <= keys, set(r) - keys)         # no dead routes

if __name__ == "__main__": unittest.main()
