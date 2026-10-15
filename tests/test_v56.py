"""v5.6: mock tests are not performance, global search, upgrade from v5.5."""
import pathlib, sys, tempfile, types, unittest
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
import config; config.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "v56.db"
import bank, classes, db, db_core, migrations, mock, progress, search  # noqa: E402
db.init_db()
n = [0]
def sid(name="Kid"):
    n[0] += 1; s = f"v56_{n[0]}"; db.ensure_student(s, name); return s
def qs(count, tag="Q", subject="Biology", topic="Cells"):
    return [{"question": f"{tag}{i} about {topic}", "options": {"A": "a", "B": "b"}, "answer": "A", "explanation": "why", "concept": "c", "subject": subject, "topic": topic} for i in range(count)]

class MockNotPerformance(unittest.TestCase):
    def test_mock_attempt_is_hidden_from_every_performance_view(self):
        s = sid()
        db.record_quiz(s, "Biology", "Cells", qs(4, "P"), {0: "A", 1: "A", 2: "B", 3: "B"}, "Medium")                     # practice: 2 of 4
        before = db.dashboard_stats(s)
        db.record_quiz(s, "Mock Test", "Full mock", qs(10, "M", topic="Mock"), {i: "B" for i in range(10)}, "Mixed", count_in_stats=False)   # 10 wrong
        after = db.dashboard_stats(s)
        self.assertEqual((after["attempted"], after["correct"], after["accuracy"]), (before["attempted"], before["correct"], before["accuracy"]))
        self.assertEqual(len(db.history(s)), 1); self.assertEqual(len(db.student_quiz_trend(s)), 1)
        self.assertNotIn("Mock", {t["topic"] for t in db.topic_mastery(s)})
    def test_mock_still_earns_xp_and_streak_and_keeps_the_attempt_row(self):
        s = sid(); db.record_quiz(s, "Mock Test", "Full mock", qs(5, "X"), {i: "A" for i in range(5)}, "Mixed", count_in_stats=False)
        self.assertGreater(progress.get_progress(s)["today_questions"], 0)
        with db_core.connect() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM quiz_attempts WHERE student_id=? AND in_stats=0", (s,)).fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM question_attempts WHERE student_id=? AND in_stats=0", (s,)).fetchone()[0], 5)
    def test_normal_quiz_still_counts(self):
        s = sid(); db.record_quiz(s, "Biology", "Cells", qs(3, "N"), {0: "A", 1: "A", 2: "A"}, "Medium")
        self.assertEqual(db.dashboard_stats(s)["attempted"], 3)
    def test_migration_flags_existing_mock_attempts(self):
        s = sid(); qid = db.record_quiz(s, "Mock Test", "Old mock", qs(3, "O", topic="OldMock"), {0: "B", 1: "B", 2: "B"}, "Mixed")   # a v5.5 mock: counted
        sc = mock.section_scores([dict(q, section="Biology") for q in qs(3, "O", topic="OldMock")], {0: "B", 1: "B", 2: "B"}, False)
        mock.save_result(s, qid, "Quick mock", sc, 60)
        self.assertEqual(db.dashboard_stats(s)["attempted"], 3)
        with db_core.connect() as con:
            migrations._m015_mock_not_performance(con)               # idempotent: the columns already exist
        db.rebuild_mastery(s)
        import db_core as c; c._WRITE_GEN += 1
        self.assertEqual(db.dashboard_stats(s)["attempted"], 0)
        self.assertEqual(len(db.history(s)), 0)
    def test_migration_registered(self):
        self.assertEqual(migrations.MIGRATIONS[-1][0], 15); self.assertGreaterEqual(db.MASTERY_MODEL_VERSION, 3)

class Search(unittest.TestCase):
    def test_pages_by_name_and_keyword(self):
        self.assertEqual(search.pages("mock", False)[0]["title"], "Mock Test")
        self.assertIn("Mistakes Diary", [r["title"] for r in search.pages("wrong", False)])
        self.assertEqual(search.pages("mock", False)[0]["icon"], "quiz")
        self.assertEqual(search.pages("zzzz", False), [])
    def test_tutor_only_sees_tutor_pages(self):
        titles = [r["title"] for r in search.pages("settings", True)]; self.assertEqual(titles, ["Settings"]); self.assertEqual(search.pages("mock", True), [])
    def test_short_or_empty_query_returns_nothing(self):
        self.assertEqual(search.search("", "x", False), []); self.assertEqual(search.search("a", "x", False), [])
    def test_student_mistakes_and_history_are_found_and_private(self):
        a, b = sid(), sid()
        db.record_quiz(a, "Chemistry", "Periodic table", qs(2, "Zinc", "Chemistry", "Periodic table"), {0: "B", 1: "A"}, "Medium")
        kinds = {r["kind"] for r in search.search("periodic", a, False)}; self.assertTrue({"Mistake", "History"} <= kinds)
        self.assertEqual([r for r in search.search("periodic", b, False) if r["kind"] != "Page"], [])
        self.assertEqual([r["route"] for r in search.search("periodic", a, False) if r["kind"] == "Mistake"], ["Mistakes Diary"])
    def test_classes_and_assignments_for_student_and_tutor(self):
        t = sid("Tutor"); st_ = sid("Stu"); c = classes.create_class(t, "FM-Junoon batch"); classes.join_class(st_, c["join_code"])
        self.assertTrue([r for r in search.search("junoon", st_, False) if r["kind"] == "Class" and r["route"] == "My Classes"])
        self.assertTrue([r for r in search.search("junoon", t, True) if r["kind"] == "Class" and r["route"] == "Tutor Dashboard"])
    def test_tutor_question_bank(self):
        t = sid("Tutor"); bank.add_question(t, {"question": "What is the powerhouse of the cell?", "options": {"A": "Mitochondria", "B": "Nucleus", "C": "x", "D": "y"}, "answer": "A", "explanation": "e", "concept": "c", "difficulty": "Easy"}, "Biology", "Cells", "manual")
        got = [r for r in search.search("powerhouse", t, True) if r["kind"] == "Question"]; self.assertEqual(len(got), 1)
    def test_html_is_not_interpreted_as_a_route(self):
        self.assertEqual(search.search("<script>", "x", False), [])

if __name__ == "__main__":
    unittest.main(verbosity=1)
