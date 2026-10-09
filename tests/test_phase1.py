"""Phase 1 tests: verify every AI callsite in main.py is wired correctly.

What these tests cover
----------------------
1. generate() — happy path returns parsed dict; timeout/bad-JSON/network-error returns None.
2. _ai_tip_task — saves an AI tip to DB; does nothing when Qwen returns None or empty.
3. POST /readings — rule-based tip written immediately; AI tip written in background.
4. GET /quiz/{reading_id} — returns AI questions when Qwen responds; falls back to DB questions.
5. POST /quiz/answer — Qwen judges right/wrong; falls back to keyword match; saves only result.
6. POST /practice — Qwen writes sentences; falls back to templates.
7. GET /health — correct flags with whisper and Ollama mocked.

Approach
--------
- A temporary SQLite DB is used (never touches data/dinig.db).
- Whisper is monkey-patched to return a fixed transcript without loading the model.
- Ollama (urllib.request.urlopen) is monkey-patched per test: happy path or failure.
- Audio conversion (to_wav) is monkey-patched to copy the input so no ffmpeg needed.
- The FastAPI test client (httpx via starlette) is used for route tests.

Run:
    venv/Scripts/python.exe tests/test_phase1.py          (Windows)
    venv/bin/python         tests/test_phase1.py          (Mac/Linux dev)
"""
import io
import json
import sys
import tempfile
import textwrap
import types
import unittest
import unittest.mock
from pathlib import Path

# ── make "backend" importable when run from the project root ──────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── patch DB and TEMP paths BEFORE importing anything that reads config ───────
import backend.config as _cfg

_tmp_dir = tempfile.mkdtemp()
_cfg.DB_PATH = Path(_tmp_dir) / "test_dinig.db"
_cfg.TEMP_DIR = Path(_tmp_dir) / "temp"
_cfg.TEMP_DIR.mkdir()
_cfg.QUIZ_TIMEOUT_SECONDS = 5.0

# ── now safe to import the rest ───────────────────────────────────────────────
import backend.db as _db
from backend.ai import local_models
from backend.ai.local_models import generate, ollama_ready

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fake_urlopen_ok(payload: dict):
    """Return a context-manager mock that yields a response with the given payload
    encoded as Ollama's outer {"response": "<json string>"} wrapper."""
    inner = json.dumps(payload)
    outer = json.dumps({"response": inner}).encode()

    class _Resp:
        def read(self):
            return outer
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass

    # json.load() reads from a file-like; wrap bytes in BytesIO
    import io as _io
    class _RespJson:
        def __enter__(self):
            return _io.BytesIO(outer)
        def __exit__(self, *_):
            pass

    return unittest.mock.patch(
        "urllib.request.urlopen",
        return_value=_RespJson(),
    )


def _fake_urlopen_error(exc=Exception("network error")):
    """Patch urlopen to raise an exception (simulates timeout / Ollama down)."""
    return unittest.mock.patch("urllib.request.urlopen", side_effect=exc)


def _make_client():
    """Build a Starlette/FastAPI test client with Whisper sentinel set."""
    from starlette.testclient import TestClient

    # Mark Whisper as loaded so whisper_loaded() returns True.
    local_models._whisper = object()  # truthy sentinel

    import backend.main as _main  # import after path/db patches

    client = TestClient(_main.app, raise_server_exceptions=True)
    return client


# Canonical patch targets (main.py imports these directly into its namespace)
_PATCH_TO_WAV       = "backend.main.to_wav"
_PATCH_CHECK        = "backend.main.check_reading"
_PATCH_TRANSCRIBE   = "backend.ai.local_models.transcribe"
_PATCH_GENERATE     = "backend.ai.local_models.generate"
_PATCH_OLLAMA_READY = "backend.ai.local_models.ollama_ready"
_PATCH_FFMPEG_EXE   = "backend.audio.ffmpeg_exe"

# Reusable fake words list (all green — a "perfect" reading)
def _perfect_words(story_text: str):
    """Return a green word list for every word in story_text."""
    from backend.text_utils import story_tokens
    return [{"word": t, "status": "green"} for t in story_text.split()]

def _mostly_red_words():
    """Return a mix with several red words so practice has targets."""
    return (
        [{"word": "lito", "status": "green"}] * 3 +
        [{"word": "bridge", "status": "red"}] +
        [{"word": "careful", "status": "red"}] +
        [{"word": "river", "status": "red"}]
    )


def _seed_minimal():
    """Insert one story + questions + one pupil into the test DB. Returns (pupil_id, story_id)."""
    _db.init_db()
    with _db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO stories (title, language, full_text, grade_level) VALUES (?, 'en', ?, 3)",
            ("The Boat on the River",
             "Lito has a small boat. Every morning he rows across the river to school. "
             "The water is calm and clear. One day it rained hard and the river was fast. "
             "Lito was careful. He tied his boat under the bridge and walked home."),
        )
        story_id = cur.lastrowid
        conn.execute("INSERT INTO questions (story_id, question, answer) VALUES (?, ?, ?)",
                     (story_id, "Where does Lito go?", "school"))
        conn.execute("INSERT INTO questions (story_id, question, answer) VALUES (?, ?, ?)",
                     (story_id, "What did Lito tie under the bridge?", "his boat"))
        cur2 = conn.execute("INSERT INTO pupils (first_name, grade) VALUES ('Mika', 3)")
        pupil_id = cur2.lastrowid
    return pupil_id, story_id


def _fake_audio():
    """Return a tiny fake .webm bytes blob (content doesn't matter; audio is mocked)."""
    return b"\x1aE\xdf\xa3"  # valid-ish WebM EBML header bytes


# ─────────────────────────────────────────────────────────────────────────────
# 1. generate() unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerate(unittest.TestCase):

    def test_happy_path_returns_parsed_dict(self):
        """generate() parses the Ollama JSON wrapper and returns the inner dict."""
        payload = {"tip": "Practice the word bridge with flashcards."}
        import io as _io
        inner = json.dumps(payload)
        outer = json.dumps({"response": inner}).encode()

        class _FakeResp:
            def __enter__(self): return _io.BytesIO(outer)
            def __exit__(self, *_): pass

        with unittest.mock.patch("urllib.request.urlopen", return_value=_FakeResp()):
            result = generate("some prompt", timeout=5.0)

        self.assertEqual(result, payload)
        self.assertEqual(result["tip"], "Practice the word bridge with flashcards.")

    def test_network_error_returns_none(self):
        """generate() returns None when Ollama is unreachable."""
        import urllib.error
        with _fake_urlopen_error(urllib.error.URLError("connection refused")):
            result = generate("some prompt", timeout=5.0)
        self.assertIsNone(result)

    def test_timeout_returns_none(self):
        """generate() returns None on socket timeout."""
        import socket
        with _fake_urlopen_error(TimeoutError("timed out")):
            result = generate("some prompt", timeout=5.0)
        self.assertIsNone(result)

    def test_bad_json_returns_none(self):
        """generate() returns None when Ollama returns non-JSON."""
        import io as _io
        garbage = b"not json at all"

        class _FakeResp:
            def __enter__(self): return _io.BytesIO(garbage)
            def __exit__(self, *_): pass

        with unittest.mock.patch("urllib.request.urlopen", return_value=_FakeResp()):
            result = generate("some prompt", timeout=5.0)
        self.assertIsNone(result)

    def test_inner_json_invalid_returns_none(self):
        """generate() returns None when the inner 'response' field is not valid JSON."""
        import io as _io
        outer = json.dumps({"response": "NOT_VALID_JSON{{"}).encode()

        class _FakeResp:
            def __enter__(self): return _io.BytesIO(outer)
            def __exit__(self, *_): pass

        with unittest.mock.patch("urllib.request.urlopen", return_value=_FakeResp()):
            result = generate("some prompt", timeout=5.0)
        self.assertIsNone(result)

    def test_uses_configured_model_and_url(self):
        """generate() sends the correct model name and URL from config."""
        import io as _io
        captured = {}

        def _capture_urlopen(req, timeout):
            captured["url"] = req.full_url
            body = json.loads(req.data)
            captured["model"] = body["model"]
            captured["stream"] = body["stream"]
            captured["format"] = body["format"]
            captured["keep_alive"] = body["keep_alive"]
            inner = json.dumps({"result": "right"})
            outer = json.dumps({"response": inner}).encode()
            class _R:
                def __enter__(self): return _io.BytesIO(outer)
                def __exit__(self, *_): pass
            return _R()

        with unittest.mock.patch("urllib.request.urlopen", side_effect=_capture_urlopen):
            generate("test prompt", timeout=5.0)

        self.assertIn("/api/generate", captured["url"])
        self.assertEqual(captured["model"], _cfg.OLLAMA_MODEL)
        self.assertFalse(captured["stream"])
        self.assertEqual(captured["format"], "json")
        self.assertEqual(captured["keep_alive"], "30m")


# ─────────────────────────────────────────────────────────────────────────────
# 2. _ai_tip_task unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAiTipTask(unittest.TestCase):

    def setUp(self):
        # Fresh DB for each test
        if _cfg.DB_PATH.exists():
            _cfg.DB_PATH.unlink()
        _db.init_db()
        with _db.connect() as conn:
            cur = conn.execute("INSERT INTO pupils (first_name, grade) VALUES ('Mika', 3)")
            self.pupil_id = cur.lastrowid

    def _get_tip(self):
        with _db.connect() as conn:
            return conn.execute("SELECT latest_tip FROM pupils WHERE id = ?",
                                (self.pupil_id,)).fetchone()["latest_tip"]

    def test_ai_tip_saved_when_qwen_responds(self):
        """_ai_tip_task updates latest_tip in DB when Qwen returns a valid tip."""
        from backend.main import _ai_tip_task
        import io as _io

        tip_text = "Try reading the word 'bridge' in short sentences."
        payload = {"tip": tip_text}
        inner = json.dumps(payload)
        outer = json.dumps({"response": inner}).encode()

        class _FakeResp:
            def __enter__(self): return _io.BytesIO(outer)
            def __exit__(self, *_): pass

        with unittest.mock.patch("urllib.request.urlopen", return_value=_FakeResp()):
            _ai_tip_task(self.pupil_id, ["bridge", "careful"])

        self.assertEqual(self._get_tip(), tip_text)

    def test_ai_tip_not_overwritten_when_qwen_fails(self):
        """_ai_tip_task leaves existing tip unchanged when Qwen returns None."""
        from backend.main import _ai_tip_task

        with _db.connect() as conn:
            conn.execute("UPDATE pupils SET latest_tip = 'Practice: bridge.' WHERE id = ?",
                         (self.pupil_id,))

        with _fake_urlopen_error():
            _ai_tip_task(self.pupil_id, ["bridge"])

        self.assertEqual(self._get_tip(), "Practice: bridge.")

    def test_ai_tip_skipped_for_empty_words(self):
        """_ai_tip_task does nothing (no DB write) when missed_words is empty."""
        from backend.main import _ai_tip_task

        with _db.connect() as conn:
            conn.execute("UPDATE pupils SET latest_tip = 'Great reading!' WHERE id = ?",
                         (self.pupil_id,))

        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            _ai_tip_task(self.pupil_id, [])
            mock_open.assert_not_called()  # Qwen never called for empty word list

        self.assertEqual(self._get_tip(), "Great reading!")

    def test_ai_tip_ignores_empty_string_in_tip(self):
        """_ai_tip_task doesn't overwrite the existing tip if Qwen returns tip=''."""
        from backend.main import _ai_tip_task
        import io as _io

        with _db.connect() as conn:
            conn.execute("UPDATE pupils SET latest_tip = 'Practice: careful.' WHERE id = ?",
                         (self.pupil_id,))

        payload = {"tip": ""}
        inner = json.dumps(payload)
        outer = json.dumps({"response": inner}).encode()

        class _FakeResp:
            def __enter__(self): return _io.BytesIO(outer)
            def __exit__(self, *_): pass

        with unittest.mock.patch("urllib.request.urlopen", return_value=_FakeResp()):
            _ai_tip_task(self.pupil_id, ["careful"])

        self.assertEqual(self._get_tip(), "Practice: careful.")


# ─────────────────────────────────────────────────────────────────────────────
# 3 & 4. API route tests (POST /readings + GET /quiz)
# ─────────────────────────────────────────────────────────────────────────────

class TestReadingsAndQuiz(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # One DB + client for all route tests
        if _cfg.DB_PATH.exists():
            _cfg.DB_PATH.unlink()
        cls.pupil_id, cls.story_id = _seed_minimal()
        cls.client = _make_client()

    def _post_reading(self, words_override=None):
        """POST a fake audio recording. Returns the JSON response.
        words_override: list of {word, status} dicts; defaults to a near-perfect reading.
        """
        words = words_override or _perfect_words(
            "lito has a small boat every morning he rows across the river to school "
            "the water is calm and clear one day it rained hard the river was fast "
            "lito was careful he tied his boat under the bridge and walked home"
        )
        summarize_result = {
            "words_correct": sum(1 for w in words if w["status"] == "green"),
            "total_words": len(words),
            "red_words": [w["word"] for w in words if w["status"] == "red"],
            "skipped_words": [w["word"] for w in words if w["status"] == "grey"],
        }
        with (
            # Patch check_reading (imported directly into main's namespace)
            unittest.mock.patch(_PATCH_CHECK, return_value=words),
            unittest.mock.patch("backend.main.summarize", return_value=summarize_result),
            # Patch to_wav so no ffmpeg is called
            unittest.mock.patch(_PATCH_TO_WAV, side_effect=lambda p: p),
            # Background AI tip: return None so test doesn't hit Ollama
            unittest.mock.patch(_PATCH_GENERATE, return_value=None),
        ):
            resp = self.client.post(
                "/readings",
                data={
                    "pupil_id": self.pupil_id,
                    "story_id": self.story_id,
                    "seconds_taken": "62.5",
                },
                files={"audio": ("reading.webm", io.BytesIO(_fake_audio()), "audio/webm")},
            )
        return resp

    def test_post_reading_returns_200_with_words(self):
        """POST /readings returns 200 with word-colored result."""
        resp = self._post_reading()
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertIn("reading_id", data)
        self.assertIn("words", data)
        self.assertIn("words_correct", data)
        self.assertIn("total_words", data)
        self.assertIn("seconds_taken", data)
        # Every word must have a valid status
        statuses = {w["status"] for w in data["words"]}
        self.assertTrue(statuses.issubset({"green", "red", "grey"}),
                        f"Unexpected statuses: {statuses}")

    def test_post_reading_saves_rule_based_tip_immediately(self):
        """After POST /readings the pupil has a tip in the DB (rule-based, not waiting for Qwen)."""
        resp = self._post_reading()
        self.assertEqual(resp.status_code, 200)
        with _db.connect() as conn:
            tip = conn.execute("SELECT latest_tip FROM pupils WHERE id = ?",
                               (self.pupil_id,)).fetchone()["latest_tip"]
        # Rule-based tip is either "Great reading!" or "Practice: word1, ..."
        self.assertIsInstance(tip, str)
        self.assertGreater(len(tip), 0)

    def test_post_reading_deletes_audio_after_scoring(self):
        """Temp audio files are deleted after scoring (privacy requirement)."""
        created_files = []

        import backend.main as _main
        original_save = _main._save_upload

        def _tracking_save(audio_upload):
            path = original_save(audio_upload)
            created_files.append(path)
            return path

        words = _perfect_words("lito has a small boat")
        summarize_result = {
            "words_correct": len(words), "total_words": len(words),
            "red_words": [], "skipped_words": [],
        }

        with (
            unittest.mock.patch("backend.main._save_upload", side_effect=_tracking_save),
            unittest.mock.patch(_PATCH_CHECK, return_value=words),
            unittest.mock.patch("backend.main.summarize", return_value=summarize_result),
            unittest.mock.patch(_PATCH_TO_WAV, side_effect=lambda p: p),
            unittest.mock.patch(_PATCH_GENERATE, return_value=None),
        ):
            resp = self.client.post(
                "/readings",
                data={"pupil_id": self.pupil_id, "story_id": self.story_id,
                      "seconds_taken": "30"},
                files={"audio": ("reading.webm", io.BytesIO(_fake_audio()), "audio/webm")},
            )
        self.assertEqual(resp.status_code, 200)
        # All files written to temp must be gone
        for p in created_files:
            self.assertFalse(p.exists(), f"Audio file not deleted: {p}")

    def test_get_quiz_returns_ai_questions_when_qwen_responds(self):
        """GET /quiz/{id} returns source='ai' when Qwen returns valid questions."""
        resp = self._post_reading()
        reading_id = resp.json()["reading_id"]

        ai_payload = {"questions": [
            {"question": "Why did Lito tie his boat?", "answer": "river was fast"},
            {"question": "Where did Lito row to?",    "answer": "school"},
        ]}
        import io as _io
        inner = json.dumps(ai_payload)
        outer = json.dumps({"response": inner}).encode()

        class _FakeResp:
            def __enter__(self): return _io.BytesIO(outer)
            def __exit__(self, *_): pass

        with unittest.mock.patch("urllib.request.urlopen", return_value=_FakeResp()):
            r = self.client.get(f"/quiz/{reading_id}")

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["source"], "ai")
        self.assertEqual(len(data["questions"]), 2)
        self.assertEqual(data["questions"][0]["question"], "Why did Lito tie his boat?")
        # AI questions have no pre-stored question_id
        self.assertIsNone(data["questions"][0]["question_id"])

    def test_get_quiz_falls_back_to_db_when_qwen_fails(self):
        """GET /quiz/{id} returns source='backup' when Qwen is unavailable."""
        resp = self._post_reading()
        reading_id = resp.json()["reading_id"]

        with _fake_urlopen_error():
            r = self.client.get(f"/quiz/{reading_id}")

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["source"], "backup")
        self.assertGreaterEqual(len(data["questions"]), 1)
        # Backup questions have a real question_id from the DB
        self.assertIsNotNone(data["questions"][0]["question_id"])

    def test_get_quiz_falls_back_when_qwen_returns_empty_list(self):
        """GET /quiz/{id} falls back when Qwen returns questions=[]."""
        resp = self._post_reading()
        reading_id = resp.json()["reading_id"]
        import io as _io

        inner = json.dumps({"questions": []})
        outer = json.dumps({"response": inner}).encode()

        class _FakeResp:
            def __enter__(self): return _io.BytesIO(outer)
            def __exit__(self, *_): pass

        with unittest.mock.patch("urllib.request.urlopen", return_value=_FakeResp()):
            r = self.client.get(f"/quiz/{reading_id}")

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["source"], "backup")


# ─────────────────────────────────────────────────────────────────────────────
# 5. POST /quiz/answer
# ─────────────────────────────────────────────────────────────────────────────

class TestQuizAnswer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if _cfg.DB_PATH.exists():
            _cfg.DB_PATH.unlink()
        cls.pupil_id, cls.story_id = _seed_minimal()
        cls.client = _make_client()
        # Post one reading so we have a reading_id and question_id to use
        words = _perfect_words("lito has a small boat every morning")
        summarize_result = {
            "words_correct": len(words), "total_words": len(words),
            "red_words": [], "skipped_words": [],
        }
        with (
            unittest.mock.patch(_PATCH_CHECK, return_value=words),
            unittest.mock.patch("backend.main.summarize", return_value=summarize_result),
            unittest.mock.patch(_PATCH_TO_WAV, side_effect=lambda p: p),
            unittest.mock.patch(_PATCH_GENERATE, return_value=None),
        ):
            resp = cls.client.post(
                "/readings",
                data={"pupil_id": cls.pupil_id, "story_id": cls.story_id,
                      "seconds_taken": "45"},
                files={"audio": ("reading.webm", io.BytesIO(_fake_audio()), "audio/webm")},
            )
        cls.reading_id = resp.json()["reading_id"]
        # Get a backup question_id from the DB
        with _db.connect() as conn:
            row = conn.execute(
                "SELECT id FROM questions WHERE story_id = ? LIMIT 1", (cls.story_id,)
            ).fetchone()
        cls.question_id = row["id"]

    def _post_answer(self, heard: str, qwen_result=None, qwen_fail=False, question_id=None):
        """Post a quiz answer with a given heard transcript. Returns JSON response."""
        import io as _io

        qid = question_id if question_id is not None else self.question_id

        ollama_up = (not qwen_fail) and (qwen_result is not None)

        if ollama_up:
            import io as _io2
            inner = json.dumps({"result": qwen_result})
            outer = json.dumps({"response": inner}).encode()
            class _FakeResp:
                def __enter__(self): return _io2.BytesIO(outer)
                def __exit__(self, *_): pass
            gen_patch = unittest.mock.patch("urllib.request.urlopen", return_value=_FakeResp())
        else:
            gen_patch = unittest.mock.patch("urllib.request.urlopen",
                                            side_effect=Exception("ollama down"))

        with (
            unittest.mock.patch(_PATCH_TRANSCRIBE, return_value=heard),
            unittest.mock.patch(_PATCH_TO_WAV, side_effect=lambda p: p),
            unittest.mock.patch(_PATCH_OLLAMA_READY, return_value=ollama_up),
            gen_patch,
        ):
            return self.client.post(
                "/quiz/answer",
                data={
                    "reading_id": self.reading_id,
                    "question": "Where does Lito go every morning?",
                    "question_id": qid,
                },
                files={"audio": ("answer.webm", _io.BytesIO(_fake_audio()), "audio/webm")},
            )

    def test_qwen_judges_right(self):
        """When Qwen returns 'right', the response is result='right'."""
        resp = self._post_answer("school", qwen_result="right")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["result"], "right")
        self.assertIn("message", data)
        self.assertGreater(len(data["message"]), 0)

    def test_qwen_judges_wrong(self):
        """When Qwen returns 'wrong', the response is result='wrong'."""
        resp = self._post_answer("i don't know", qwen_result="wrong")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], "wrong")

    def test_fallback_keyword_match_right(self):
        """When Qwen is down, keyword match against backup answer works for 'right'."""
        # The backup answer is "school" — the child says "I go to school"
        resp = self._post_answer("i go to school", qwen_fail=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], "right")

    def test_fallback_keyword_match_wrong(self):
        """When Qwen is down, keyword match returns 'wrong' for an irrelevant answer."""
        resp = self._post_answer("i like mangoes", qwen_fail=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], "wrong")

    def test_no_question_id_gives_unchecked(self):
        """When question_id is None and Qwen is down, result is 'unchecked'."""
        import io as _io
        with (
            unittest.mock.patch(_PATCH_TRANSCRIBE, return_value="hmm"),
            unittest.mock.patch(_PATCH_TO_WAV, side_effect=lambda p: p),
            unittest.mock.patch(_PATCH_OLLAMA_READY, return_value=False),
        ):
            resp = self.client.post(
                "/quiz/answer",
                data={
                    "reading_id": self.reading_id,
                    "question": "An AI question with no stored answer.",
                    # no question_id field
                },
                files={"audio": ("answer.webm", _io.BytesIO(_fake_audio()), "audio/webm")},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], "unchecked")

    def test_answer_audio_deleted(self):
        """Quiz answer audio must be deleted after transcription."""
        created = []
        import backend.main as _main
        orig = _main._save_upload

        def _track(upload):
            p = orig(upload)
            created.append(p)
            return p

        import io as _io
        with (
            unittest.mock.patch("backend.main._save_upload", side_effect=_track),
            unittest.mock.patch(_PATCH_TRANSCRIBE, return_value="school"),
            unittest.mock.patch(_PATCH_TO_WAV, side_effect=lambda p: p),
            unittest.mock.patch(_PATCH_OLLAMA_READY, return_value=False),
        ):
            self.client.post(
                "/quiz/answer",
                data={"reading_id": self.reading_id,
                      "question": "Where does Lito go?",
                      "question_id": self.question_id},
                files={"audio": ("answer.webm", _io.BytesIO(_fake_audio()), "audio/webm")},
            )

        for p in created:
            self.assertFalse(p.exists(), f"Answer audio not deleted: {p}")

    def test_result_saved_to_db(self):
        """Quiz results are saved to quiz_answers table (result only, no transcript)."""
        resp = self._post_answer("school", qwen_result="right")
        self.assertEqual(resp.status_code, 200)
        with _db.connect() as conn:
            row = conn.execute(
                "SELECT result FROM quiz_answers WHERE reading_id = ? ORDER BY id DESC LIMIT 1",
                (self.reading_id,)
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["result"], "right")


# ─────────────────────────────────────────────────────────────────────────────
# 6. POST /practice
# ─────────────────────────────────────────────────────────────────────────────

class TestPractice(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if _cfg.DB_PATH.exists():
            _cfg.DB_PATH.unlink()
        cls.pupil_id, cls.story_id = _seed_minimal()
        cls.client = _make_client()
        # Post a reading with several red words so practice has targets
        words = _mostly_red_words()
        summarize_result = {
            "words_correct": sum(1 for w in words if w["status"] == "green"),
            "total_words": len(words),
            "red_words": [w["word"] for w in words if w["status"] == "red"],
            "skipped_words": [],
        }
        with (
            unittest.mock.patch(_PATCH_CHECK, return_value=words),
            unittest.mock.patch("backend.main.summarize", return_value=summarize_result),
            unittest.mock.patch(_PATCH_TO_WAV, side_effect=lambda p: p),
            unittest.mock.patch(_PATCH_GENERATE, return_value=None),
        ):
            resp = cls.client.post(
                "/readings",
                data={"pupil_id": cls.pupil_id, "story_id": cls.story_id,
                      "seconds_taken": "30"},
                files={"audio": ("reading.webm", io.BytesIO(_fake_audio()), "audio/webm")},
            )
        cls.reading_id = resp.json()["reading_id"]

    def test_practice_returns_ai_sentences_when_qwen_responds(self):
        """POST /practice returns Qwen sentences when Qwen is available."""
        import io as _io
        ai_payload = {"sentences": [
            "The bridge was old but strong.",
            "Lito was careful on the bridge.",
        ]}
        inner = json.dumps(ai_payload)
        outer = json.dumps({"response": inner}).encode()

        class _FakeResp:
            def __enter__(self): return _io.BytesIO(outer)
            def __exit__(self, *_): pass

        with unittest.mock.patch("urllib.request.urlopen", return_value=_FakeResp()):
            resp = self.client.post("/practice",
                                    json={"reading_id": self.reading_id})

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("sentences", data)
        self.assertEqual(data["sentences"], ai_payload["sentences"])

    def test_practice_falls_back_to_templates_when_qwen_fails(self):
        """POST /practice returns template sentences when Qwen is unavailable."""
        with _fake_urlopen_error():
            resp = self.client.post("/practice",
                                    json={"reading_id": self.reading_id})

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("sentences", data)
        # Template: "I can read the word <word>."
        for s in data["sentences"]:
            self.assertTrue(s.startswith("I can read the word "),
                            f"Unexpected template: {s!r}")

    def test_practice_has_target_words_and_wrong_before(self):
        """POST /practice always returns target_words and wrong_before."""
        with _fake_urlopen_error():
            resp = self.client.post("/practice",
                                    json={"reading_id": self.reading_id})

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("target_words", data)
        self.assertIn("wrong_before", data)
        self.assertIn("practice_id", data)
        self.assertGreater(data["wrong_before"], 0)
        self.assertGreater(len(data["target_words"]), 0)

    def test_practice_targets_at_most_3_words(self):
        """POST /practice uses at most 3 target words (cap from main.py)."""
        with _fake_urlopen_error():
            resp = self.client.post("/practice",
                                    json={"reading_id": self.reading_id})

        data = resp.json()
        self.assertLessEqual(len(data["target_words"]), 3)


# ─────────────────────────────────────────────────────────────────────────────
# 7. GET /health
# ─────────────────────────────────────────────────────────────────────────────

class TestHealth(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if _cfg.DB_PATH.exists():
            _cfg.DB_PATH.unlink()
        _seed_minimal()
        cls.client = _make_client()

    def test_health_all_ok(self):
        """GET /health returns all true when everything is mocked as available."""
        import io as _io
        tags_payload = {"models": [{"name": _cfg.OLLAMA_MODEL}]}

        class _FakeTagsResp:
            def __enter__(self): return _io.BytesIO(json.dumps(tags_payload).encode())
            def __exit__(self, *_): pass

        with (
            unittest.mock.patch("urllib.request.urlopen", return_value=_FakeTagsResp()),
            unittest.mock.patch("backend.audio.ffmpeg_exe", return_value="/usr/bin/ffmpeg"),
        ):
            resp = self.client.get("/health")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["whisper_loaded"])
        self.assertTrue(data["ollama_ready"])
        self.assertTrue(data["ffmpeg_found"])
        self.assertTrue(data["db_ok"])
        self.assertEqual(data["ollama_model"], _cfg.OLLAMA_MODEL)

    def test_health_whisper_not_loaded(self):
        """GET /health reports whisper_loaded=false when Whisper sentinel is None."""
        original = local_models._whisper
        local_models._whisper = None
        try:
            import io as _io
            tags_payload = {"models": [{"name": _cfg.OLLAMA_MODEL}]}
            class _FakeTagsResp:
                def __enter__(self): return _io.BytesIO(json.dumps(tags_payload).encode())
                def __exit__(self, *_): pass
            with (
                unittest.mock.patch("urllib.request.urlopen", return_value=_FakeTagsResp()),
                unittest.mock.patch("backend.audio.ffmpeg_exe", return_value="/usr/bin/ffmpeg"),
            ):
                resp = self.client.get("/health")
            self.assertFalse(resp.json()["whisper_loaded"])
        finally:
            local_models._whisper = original  # restore for other tests

    def test_health_ollama_not_ready(self):
        """GET /health reports ollama_ready=false when Ollama is down."""
        with (
            _fake_urlopen_error(),
            unittest.mock.patch("backend.audio.ffmpeg_exe", return_value="/usr/bin/ffmpeg"),
        ):
            resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["ollama_ready"])


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

def _run():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestGenerate,
        TestAiTipTask,
        TestReadingsAndQuiz,
        TestQuizAnswer,
        TestPractice,
        TestHealth,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print()
    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed
    print(f"{'All' if not failed else str(passed) + ' of'} {total} Phase 1 tests passed."
          + (" ✓" if not failed else f"  {failed} FAILED."))
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    _run()
