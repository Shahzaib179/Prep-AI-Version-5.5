"""v5.4: Mistakes Diary, calendar study plan, career profile wizard logic, tutor settings storage, upgrade from v5.3."""
import pathlib, sys, tempfile, types, unittest
from datetime import date, datetime
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
import config; config.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "v54.db"
import db, db_core, diary, migrations, navigation, plan_calendar as pc, career_profile as cp, pathfinder_service as pf, progress  # noqa: E402
db.init_db()
n = [0]
def sid():
    n[0] += 1; s = f"v54_{n[0]}"; db.ensure_student(s, "Kid"); return s
def qs(count, tag="Q"):
    return [{"question": f"{tag}{i}", "options": {"A": "a", "B": "b"}, "answer": "A", "explanation": f"why {i}", "concept": "c", "subject": "Biology", "topic": "Cells"} for i in range(count)]

class Diary(unittest.TestCase):
    def test_wrong_answers_appear_skipped_and_correct_do_not(self):
        s = sid(); db.record_quiz(s, "Biology", "Cells", qs(4), {0: "B", 1: "B", 2: "A"}, "Medium")        # 2 wrong, 1 right, 1 skipped
        got = diary.open_mistakes(s); self.assertEqual(sorted(m["question"] for m in got), ["Q0", "Q1"]); self.assertEqual(diary.open_count(s), 2)
        m = got[0]; self.assertEqual((m["correct"], m["wrong"]), ("A", "B")); self.assertEqual(diary.option_text(m, "A"), "A. a")
    def test_resolve_removes_and_count_drops_immediately(self):
        s = sid(); db.record_quiz(s, "Biology", "Cells", qs(3), {0: "B", 1: "B", 2: "B"}, "Medium")
        first = diary.open_mistakes(s)[0]; self.assertEqual(diary.open_count(s), 3)
        self.assertEqual(diary.resolve(s, first["id"]), 1); self.assertEqual(diary.open_count(s), 2)        # no 30 s cache delay
        self.assertNotIn(first["id"], [m["id"] for m in diary.open_mistakes(s)])
        with db_core.connect() as con:                                                                       # nothing is deleted
            self.assertEqual(con.execute("SELECT COUNT(*) FROM mistakes WHERE student_id=?", (s,)).fetchone()[0], 3)
    def test_same_question_wrong_twice_is_one_entry_and_resolves_together(self):
        s = sid(); db.record_quiz(s, "Biology", "t", qs(1), {0: "B"}, "Medium"); db.record_quiz(s, "Biology", "t", qs(1), {0: "B"}, "Medium")
        self.assertEqual(diary.open_count(s), 1); diary.resolve(s, diary.open_mistakes(s)[0]["id"]); self.assertEqual(diary.open_count(s), 0)
    def test_answering_correctly_later_removes_it(self):
        s = sid(); db.record_quiz(s, "Biology", "t", qs(2), {0: "B", 1: "B"}, "Medium"); self.assertEqual(diary.open_count(s), 2)
        db.record_quiz(s, "Biology", "t", qs(1), {0: "A"}, "Medium"); self.assertEqual([m["question"] for m in diary.open_mistakes(s)], ["Q1"])
    def test_students_are_isolated(self):
        a, b = sid(), sid(); db.record_quiz(a, "Biology", "t", qs(2), {0: "B", 1: "B"}, "Medium")
        self.assertEqual(diary.open_count(b), 0); diary.resolve(b, diary.open_mistakes(a)[0]["id"]); self.assertEqual(diary.open_count(a), 2)   # b cannot resolve a's mistake
    def test_prompt_and_fallback_use_only_stored_text(self):
        s = sid(); db.record_quiz(s, "Biology", "Cells", qs(1), {0: "B"}, "Medium"); m = diary.open_mistakes(s)[0]
        self.assertIn("Q0", diary.teach_prompt(m)); self.assertIn("why 0", diary.fallback_teaching(m)); self.assertIn("could not be reached", diary.fallback_teaching(m))
    def test_old_mistakes_without_options_still_listed(self):
        s = sid()
        with db_core.connect() as con:
            con.execute("INSERT INTO mistakes(student_id,subject,topic,concept,question_text,wrong_answer,correct_answer,explanation,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (s, "Physics", "", "", "Old Q", "C", "B", "", "2026-01-01"))
        m = diary.open_mistakes(s)[0]; self.assertEqual((m["subject"], m["options"]), ("Physics", {})); self.assertEqual(diary.option_text(m, "C"), "C")
    def test_many_mistakes_query_is_chunked(self):
        s = sid(); db.record_quiz(s, "Biology", "t", qs(450, "Big"), {i: "B" for i in range(450)}, "Medium"); self.assertEqual(diary.open_count(s), 450)

class Nav(unittest.TestCase):
    def test_diary_in_student_nav_and_tutor_settings(self):
        self.assertIn("Mistakes Diary", navigation.routes(False)); self.assertEqual(navigation.routes(True), ["Tutor Dashboard", "Settings"])
        self.assertEqual(navigation.resolve("Mistakes Diary", False), "Mistakes Diary"); self.assertEqual(navigation.resolve("Mistakes Diary", True), "Tutor Dashboard")
    def test_badge_css(self):
        self.assertEqual(navigation.badge_css("Mistakes Diary", 0), ""); self.assertIn('content: "20"', navigation.badge_css("Mistakes Diary", 20)); self.assertIn('"99+"', navigation.badge_css("Mistakes Diary", 150))
        self.assertIn("mistakes_diary", navigation.badge_css("Mistakes Diary", 3))

PLAN = [{"day": "Day 1", "sessions": [{"subject": "Biology", "topic": "Cell <b>cycle</b>", "minutes": 60, "activity": "Read notes", "source": "Bio.pdf p.2"},
                                      {"subject": "Chemistry", "topic": "Bonding", "minutes": 45, "activity": "Practice MCQs"}]},
        {"day": "Day 2", "sessions": [{"subject": "Physics", "topic": "Optics", "minutes": 90, "activity": "Revision"}]}]
class Calendar(unittest.TestCase):
    def test_sessions_follow_each_other_without_overlap(self):
        days = pc.layout(PLAN, date(2026, 10, 15), 17 * 60); e = days[0]["events"]
        self.assertEqual((e[0]["start"], e[0]["end"], e[1]["start"], e[1]["end"]), (1020, 1080, 1090, 1135)); self.assertEqual(days[1]["weekday"], "FRI")
    def test_late_day_is_moved_earlier_not_cut(self):
        d = pc.layout([{"sessions": [{"minutes": 120, "topic": "x"}]}], date(2026, 10, 15), 23 * 60)[0]["events"][0]; self.assertEqual((d["start"], d["end"]), (22 * 60, 24 * 60))
    def test_html_escapes_text_and_marks_planned_and_today(self):
        days = pc.layout(PLAN, date(2026, 10, 15), 17 * 60); html = pc.to_html(days, datetime(2026, 10, 15, 17, 30))
        self.assertNotIn("<b>cycle", html); self.assertIn("&lt;b&gt;cycle", html); self.assertIn("cal-now", html); self.assertIn("planned", html); self.assertIn("17:00 - 18:00", html)
    def test_bad_input_does_not_crash(self):
        self.assertEqual(pc.layout([None, "x", {"sessions": [None, {"minutes": "abc"}]}], date(2026, 10, 15))[0]["events"][0]["minutes"], 30)
        self.assertEqual(pc.parse_start("nonsense"), 17 * 60); self.assertEqual(pc.to_html([]), "")
    def test_ics_is_valid_and_stable(self):
        days = pc.layout(PLAN, date(2026, 10, 15)); a = pc.to_ics(days, stamp=datetime(2026, 1, 1)); b = pc.to_ics(days, stamp=datetime(2026, 1, 1))
        self.assertEqual(a, b); self.assertEqual(a.count("BEGIN:VEVENT"), 3); self.assertIn("DTSTART:20261015T170000", a); self.assertTrue(a.startswith("BEGIN:VCALENDAR\r\n")); self.assertTrue(all(len(x.encode()) <= 75 for x in a.split("\r\n")))
        self.assertEqual(len(set(x for x in a.split("\r\n") if x.startswith("UID:"))), 3)

class Career(unittest.TestCase):
    def test_weights_add_to_100_and_scoring(self):
        self.assertEqual(sum(w for _, _, w in cp.CRITERIA), 100)
        self.assertEqual(cp.weighted_percent({k: 5 for k, _, _ in cp.CRITERIA}), 100.0); self.assertEqual(cp.weighted_percent({k: 1 for k, _, _ in cp.CRITERIA}), 20.0)
        self.assertEqual(cp.weighted_percent({}), 60.0)                                                     # untouched criteria are neutral (3 of 5)
        self.assertEqual(cp.weighted_percent({"interest": 99, "aptitude": "x"}), round(20 * 5 / 5 + 20 * 3 / 5 + 20 * 3 / 5 + 15 * 3 / 5 + 10 * 3 / 5 + 10 * 3 / 5 + 5 * 3 / 5, 1))
    def test_ranking_ignores_unnamed_and_caps_at_three(self):
        hi = {k: 5 for k, _, _ in cp.CRITERIA}; lo = {k: 2 for k, _, _ in cp.CRITERIA}
        r = cp.rank_options([{"name": "Low", "scores": lo}, {"name": " ", "scores": hi}, {"name": "High", "scores": hi}, {"name": "Mid", "scores": {}}, {"name": "Fourth", "scores": hi}])
        self.assertEqual([x["name"] for x in r], ["High", "Low"]); self.assertNotIn("Fourth", [x["name"] for x in r])      # only the first three slots count; a blank slot is ignored
    def test_stream_questions(self):
        for s in pf.STREAMS: self.assertEqual(len(cp.stream_questions(s)), 4)
        self.assertIn("MDCAT", cp.stream_questions("Pre-Medical")[3])
    def test_profile_reaches_pathfinder_in_its_own_format(self):
        data = {"stream": "Pre-Medical", "level": pf.LEVELS[2], "interests": ["Medicine & healthcare"], "fsc_pct": 82.0, "matric_pct": 0, "family_income": 30000.0, "annual_budget": 0,
                "career_aim": "Doctor", "backup": "Pharm-D", "degree1": "MBBS", "degree2": "", "universities": "KMU; UHS\nAKU", "options": [{"name": "MBBS", "scores": {}}]}
        p = cp.to_pf_profile(data); self.assertEqual((p["stream"], p["fsc_pct"], p["family_income"]), ("Pre-Medical", 82.0, 30000.0)); self.assertNotIn("matric_pct", p)
        self.assertEqual(p["universities_considering"], ["KMU", "UHS", "AKU"]); self.assertIn("Backup if not admitted: Pharm-D", p["goals"]); self.assertEqual(p["own_comparison"][0]["option"], "MBBS")
        kb = pf.load_kb(); self.assertTrue(pf.match_programs(kb, p)); pf.build_prompt(p, [])           # the existing pipeline accepts it unchanged
    def test_recommendation_uses_students_words_and_verified_programs(self):
        kb = pf.load_kb(); data = {"stream": "Pre-Medical", "universities": "A\nB\nC\nD\nE\nF", "backup": "Nursing", "options": [{"name": "MBBS", "scores": {k: 5 for k, _, _ in cp.CRITERIA}}]}
        rec = cp.recommendation(data, pf.match_programs(kb, cp.to_pf_profile(data)))
        self.assertEqual(len(rec["degrees"]), 3); self.assertTrue(rec["degrees"][0]["own"]); self.assertFalse(rec["degrees"][1]["own"]); self.assertEqual(len(rec["universities"]), 5); self.assertEqual(rec["backup"], "Nursing")
        empty = cp.recommendation({}, []); self.assertEqual((empty["degrees"], empty["universities"], empty["backup"]), ([], [], ""))
    def test_save_load_resume_and_income_never_stored(self):
        s = sid(); self.assertEqual(cp.load(s), ({}, 0))
        cp.save(s, {"stream": "ICS (Computer Science)", "family_income": 1234.0, "degree1": "BS CS"}, 3); d, step = cp.load(s)
        self.assertEqual((d["stream"], step), ("ICS (Computer Science)", 3)); self.assertNotIn("family_income", d)
        cp.save(s, {"stream": "Pre-Medical"}, 5); self.assertEqual(cp.load(s), ({"stream": "Pre-Medical"}, 5)); cp.clear(s); self.assertEqual(cp.load(s), ({}, 0))
    def test_missing_fields_reported(self):
        self.assertEqual(len(cp.missing_for_run({})), 3); self.assertEqual(cp.missing_for_run({"stream": "x", "interests": ["a"], "fsc_pct": 70}), [])

class TutorPrefsAndUpgrade(unittest.TestCase):
    def test_tutor_defaults_round_trip(self):
        s = sid(); db.update_preferences(s, tutor_difficulty="Hard", tutor_count=30, tutor_minutes=15, llm_model="openai/gpt-oss-20b")
        p = db.get_preferences(s); self.assertEqual((p["tutor_difficulty"], p["tutor_count"], p["tutor_minutes"], p["llm_model"]), ("Hard", 30, 15, "openai/gpt-oss-20b"))
        db.update_preferences(s, evil_column="x"); self.assertNotIn("evil_column", db.get_preferences(s))
    def test_upgrade_from_v53_keeps_data_and_cleans_game_mistakes(self):
        path = pathlib.Path(tempfile.mkdtemp()) / "old.db"; old_path = config.DB_PATH; full = list(migrations.MIGRATIONS)
        try:
            config.DB_PATH = path; pass
            migrations.MIGRATIONS = [m for m in full if m[0] <= 13]; self.assertEqual(migrations.migrate()[-1], 13)
            with db_core.connect() as con:
                con.execute("INSERT INTO students(id,name,created_at,updated_at) VALUES('o1','Old','2026-01-01','2026-01-01')")
                con.execute("INSERT INTO mistakes(student_id,subject,question_text,wrong_answer,correct_answer,created_at) VALUES('o1','Biology','Normal Q','B','A','2026-01-01T10:00')")
                con.execute("INSERT INTO mistakes(student_id,subject,question_text,wrong_answer,correct_answer,created_at) VALUES('o1','Biology','Game Q','B','A','2026-01-02T10:00')")
                con.execute("INSERT INTO quiz_attempts(id,student_id,subject,topic,total,created_at) VALUES(900,'o1','Biology','Quick MCQ Challenge',1,'2026-01-02T10:00')")
                con.execute("INSERT INTO game_results(student_id,game,subject,correct,total,quiz_id,day,created_at) VALUES('o1','quick','Biology',0,1,900,'2026-01-02','2026-01-02')")
            migrations.MIGRATIONS = full; self.assertEqual(migrations.migrate(), [14, 15]); self.assertEqual(migrations.migrate(), [])
            with db_core.connect() as con:
                self.assertEqual([r[0] for r in con.execute("SELECT question_text FROM mistakes WHERE student_id='o1'").fetchall()], ["Normal Q"])
                con.execute("SELECT resolved_at FROM mistakes LIMIT 1"); con.execute("SELECT data_json FROM career_profiles LIMIT 1"); con.execute("SELECT tutor_count FROM student_preferences LIMIT 1")
        finally:
            migrations.MIGRATIONS = full; config.DB_PATH = old_path

if __name__ == "__main__":
    unittest.main()
