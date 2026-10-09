"""Dinig backend: FastAPI on http://localhost:8000. Serves the API and the frontend.

Start it with start_dinig.bat (or for development):
    venv\\Scripts\\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
"""
import logging
import shutil
import subprocess
import uuid
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import config, db
from backend.ai import local_models
from backend.audio import ffmpeg_exe, to_wav
from backend.reading_check import check_reading, summarize
from backend.text_utils import clean_story, normalize
from backend.text_utils import words as text_words
from backend.tips import rule_based_tip

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dinig")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    with db.connect() as conn:
        empty = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0] == 0
    if empty:  # first run: load the sample class so the app is never blank
        from backend.seed import seed
        seed()
    config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    for pattern in ("*.webm", "*.wav"):  # audio left by a crash or power cut
        for leftover in config.TEMP_DIR.glob(pattern):
            try:
                leftover.unlink()
            except OSError:
                log.warning("Could not delete leftover audio %s", leftover.name)
    local_models.load_whisper()  # loaded ONCE here, never per request
    yield


app = FastAPI(title="Dinig", lifespan=lifespan)


# ---------- Health ----------

@app.get("/health")
def health():
    return {
        "whisper_loaded": local_models.whisper_loaded(),
        "ollama_ready": local_models.ollama_ready(),
        "ollama_model": config.OLLAMA_MODEL,
        "ffmpeg_found": ffmpeg_exe() is not None,
        "db_ok": db.db_ok(),
    }


# ---------- Pupils ----------

class NewPupil(BaseModel):
    first_name: str = Field(min_length=1, max_length=40)
    class_no: str | None = Field(default=None, max_length=10)
    grade: int = Field(ge=1, le=6)


@app.get("/pupils")
def list_pupils():
    with db.connect() as conn:
        rows = conn.execute("SELECT id, first_name, class_no, grade FROM pupils ORDER BY first_name").fetchall()
    return [dict(r) for r in rows]


@app.post("/pupils", status_code=201)
def add_pupil(p: NewPupil):
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO pupils (first_name, class_no, grade) VALUES (?, ?, ?)",
            (p.first_name.strip(), (p.class_no or "").strip() or None, p.grade),
        )
        row = conn.execute("SELECT id, first_name, class_no, grade FROM pupils WHERE id = ?",
                           (cur.lastrowid,)).fetchone()
    return dict(row)


# ---------- Stories ----------

@app.get("/stories")
def list_stories():
    with db.connect() as conn:
        rows = conn.execute("SELECT id, title, language, grade_level FROM stories ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@app.get("/stories/{story_id}")
def get_story(story_id: int):
    with db.connect() as conn:
        row = conn.execute("SELECT id, title, full_text FROM stories WHERE id = ?", (story_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Story not found")
    return {"id": row["id"], "title": row["title"], "full_text": clean_story(row["full_text"]),
            "placeholder": row["full_text"] != clean_story(row["full_text"])}


# ---------- Read and Check ----------

def _save_upload(audio: UploadFile) -> Path:
    path = config.TEMP_DIR / f"{uuid.uuid4().hex}.webm"
    with open(path, "wb") as f:
        shutil.copyfileobj(audio.file, f)
    return path


def _delete(*paths) -> None:
    for p in paths:
        if p is not None:
            Path(p).unlink(missing_ok=True)


def _ai_tip_task(pupil_id: int, missed_words: list[str]) -> None:
    """Background task: ask Qwen for a one-sentence teacher tip and save it.
    If Qwen is unavailable the rule-based tip written before this task runs stays."""
    unique = list(dict.fromkeys(w for w in missed_words if w))[:5]
    if not unique:
        return  # rule-based tip ("Great reading!") is already correct
    prompt = (
        f"A Grade 3 pupil struggled with these words: {', '.join(unique)}. "
        "Write one short, encouraging tip for their teacher in plain English. "
        'Return JSON: {"tip": "..."}'
    )
    result = local_models.generate(prompt, timeout=config.QUIZ_TIMEOUT_SECONDS)
    tip = result.get("tip", "").strip() if result else ""
    if tip:
        with db.connect() as conn:
            conn.execute("UPDATE pupils SET latest_tip = ? WHERE id = ?", (tip, pupil_id))


@app.post("/readings")
def create_reading(
    background_tasks: BackgroundTasks,
    pupil_id: int = Form(...),
    story_id: int = Form(...),
    seconds_taken: float = Form(...),
    audio: UploadFile = File(...),
):
    """Convert, score, save, delete the audio, save a rule-based tip, return colored words.
    A sync def: FastAPI runs it in a worker thread, so Whisper doesn't block the server."""
    with db.connect() as conn:
        story = conn.execute("SELECT full_text, language FROM stories WHERE id = ?", (story_id,)).fetchone()
        pupil = conn.execute("SELECT id FROM pupils WHERE id = ?", (pupil_id,)).fetchone()
    if not story or not pupil:
        raise HTTPException(404, "Pupil or story not found")
    if not local_models.whisper_loaded():
        raise HTTPException(503, "Whisper is not loaded. Check /health.")

    webm = wav = None
    try:
        webm = _save_upload(audio)
        wav = to_wav(webm)
        words = check_reading(wav, story["full_text"], story["language"])
    except subprocess.CalledProcessError:
        raise HTTPException(400, "Could not read the recording. Please try again.")
    finally:
        _delete(webm, wav)  # privacy: children's audio never stays on disk

    s = summarize(words)
    seconds = max(1, round(seconds_taken))
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO readings (pupil_id, story_id, read_at, seconds_taken, words_correct, total_words, "
            "red_words, skipped_words) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pupil_id, story_id, datetime.now().replace(microsecond=0).isoformat(sep=" "), seconds,
             s["words_correct"], s["total_words"], db.to_json(s["red_words"]), db.to_json(s["skipped_words"])),
        )
        reading_id = cur.lastrowid
        conn.execute("UPDATE pupils SET latest_tip = ? WHERE id = ?",
                     (rule_based_tip(s["red_words"] + s["skipped_words"]), pupil_id))
    # Replace the rule-based tip with an AI-generated one in the background so
    # the reading result returns immediately while Qwen thinks.
    background_tasks.add_task(_ai_tip_task, pupil_id, s["red_words"] + s["skipped_words"])

    return {"reading_id": reading_id, "words": words, "words_correct": s["words_correct"],
            "total_words": s["total_words"], "seconds_taken": seconds}


# ---------- Story Quiz (backup questions for now) ----------

STOPWORDS = {"the", "and", "because", "was", "his", "her", "him", "they", "them", "she", "into",
             "with", "for", "from", "that", "this", "are", "has", "had", "did", "does", "its"}
MESSAGES = {
    "right": "Yes! Great thinking!",
    "wrong": "Not yet. Good try! The answer is in the story.",
    "unchecked": "Good thinking!",
}


def _keyword_match(answer: str, heard: str) -> bool:
    """Right if any key word of the saved answer was said ("rained" matches "rain")."""
    keys = [w for w in text_words(answer) if len(w) >= 3 and w not in STOPWORDS]
    said = text_words(heard)
    return any(h.startswith(k[:4]) for k in keys for h in said)


@app.get("/quiz/{reading_id}")
def get_quiz(reading_id: int):
    with db.connect() as conn:
        reading = conn.execute("SELECT story_id FROM readings WHERE id = ?", (reading_id,)).fetchone()
        if not reading:
            raise HTTPException(404, "Reading not found")
        rows = conn.execute("SELECT id, question FROM questions WHERE story_id = ? ORDER BY id LIMIT 2",
                            (reading["story_id"],)).fetchall()
        story_row = conn.execute(
            "SELECT full_text FROM stories WHERE id = ?", (reading["story_id"],)
        ).fetchone()
    # Ask Qwen for 2 questions; fall back to pre-written backup questions if it
    # is slow or unavailable. QUIZ_TIMEOUT_SECONDS (default 8s) keeps the pupil waiting.
    story_text = clean_story(story_row["full_text"])
    prompt = (
        f"Read this story and write 2 comprehension questions for a Grade 3 pupil.\n"
        f"Story: {story_text}\n"
        'Return JSON: {"questions": [{"question": "...", "answer": "..."}, {"question": "...", "answer": "..."}]}'
    )
    ai = local_models.generate(prompt, timeout=config.QUIZ_TIMEOUT_SECONDS)
    if ai and isinstance(ai.get("questions"), list) and len(ai["questions"]) >= 1:
        questions = [
            {"question_id": None, "question": q["question"]}
            for q in ai["questions"][:2]
            if q.get("question")
        ]
        if questions:
            return {"source": "ai", "questions": questions}
    # fallback: pre-written backup questions from the DB
    return {"source": "backup", "questions": [{"question_id": r["id"], "question": r["question"]} for r in rows]}


@app.post("/quiz/answer")
def quiz_answer(
    reading_id: int = Form(...),
    question: str = Form(...),
    question_id: int | None = Form(None),
    audio: UploadFile = File(...),
):
    with db.connect() as conn:
        reading = conn.execute("SELECT r.id, s.language FROM readings r JOIN stories s ON s.id = r.story_id "
                               "WHERE r.id = ?", (reading_id,)).fetchone()
        backup = conn.execute("SELECT answer FROM questions WHERE id = ?", (question_id,)).fetchone() \
            if question_id else None
    if not reading:
        raise HTTPException(404, "Reading not found")
    if not local_models.whisper_loaded():
        raise HTTPException(503, "Whisper is not loaded. Check /health.")

    webm = wav = None
    try:
        webm = _save_upload(audio)
        wav = to_wav(webm)
        heard = local_models.transcribe(wav, reading["language"])
    except subprocess.CalledProcessError:
        raise HTTPException(400, "Could not read the recording. Please try again.")
    finally:
        _delete(webm, wav)

    # Ask Qwen to judge the answer; fall back to keyword match when Qwen is slow or off.
    judged = False
    if local_models.ollama_ready():
        with db.connect() as conn2:
            story_row = conn2.execute(
                "SELECT s.full_text FROM stories s JOIN readings r ON r.story_id = s.id WHERE r.id = ?",
                (reading_id,)
            ).fetchone()
        if story_row:
            judge_prompt = (
                f"Story: {clean_story(story_row['full_text'])}\n"
                f"Question: {question}\n"
                f"Pupil said: {heard}\n"
                "Is the pupil's answer correct? "
                'Return JSON: {"result": "right" or "wrong"}'
            )
            ai = local_models.generate(judge_prompt, timeout=config.QUIZ_TIMEOUT_SECONDS)
            if ai and ai.get("result") in ("right", "wrong"):
                result = ai["result"]
                judged = True
    if not judged:
        # fallback: keyword match against the pre-written backup answer
        if backup:
            result = "right" if _keyword_match(backup["answer"], heard) else "wrong"
        else:
            result = "unchecked"
    with db.connect() as conn:  # privacy: only the result is saved, never what the child said
        conn.execute("INSERT INTO quiz_answers (reading_id, question, result) VALUES (?, ?, ?)",
                     (reading_id, question, result))
    return {"result": result, "message": MESSAGES[result]}


# ---------- Practice Again (template sentences for now) ----------

class PracticeRequest(BaseModel):
    reading_id: int


@app.post("/practice")
def create_practice(req: PracticeRequest):
    with db.connect() as conn:
        reading = conn.execute("SELECT red_words FROM readings WHERE id = ?", (req.reading_id,)).fetchone()
        if not reading:
            raise HTTPException(404, "Reading not found")
        targets = list(dict.fromkeys(db.from_json(reading["red_words"])))[:3]
        # Ask Qwen for natural practice sentences using the missed words.
        # Fall back to simple templates when Qwen is unavailable.
        ai_sentences = None
        if targets:
            prompt = (
                f"Write 2 short, easy sentences for a Grade 3 Filipino pupil. "
                f"Each sentence must use one of these words: {', '.join(targets)}. "
                "Use simple English. "
                'Return JSON: {"sentences": ["...", "..."]}'
            )
            ai = local_models.generate(prompt, timeout=config.QUIZ_TIMEOUT_SECONDS)
            if ai and isinstance(ai.get("sentences"), list) and len(ai["sentences"]) >= 1:
                ai_sentences = [s for s in ai["sentences"] if isinstance(s, str) and s.strip()]
        sentences = ai_sentences if ai_sentences else [f"I can read the word {w}." for w in targets]
        cur = conn.execute("INSERT INTO practice (reading_id, sentences, wrong_before) VALUES (?, ?, ?)",
                           (req.reading_id, db.to_json(sentences), len(targets)))
    return {"practice_id": cur.lastrowid, "sentences": sentences, "target_words": targets,
            "wrong_before": len(targets)}


@app.post("/practice/{practice_id}/check")
def check_practice(practice_id: int, audio: UploadFile = File(...)):
    with db.connect() as conn:
        row = conn.execute("SELECT p.sentences, p.wrong_before, r.red_words, s.language FROM practice p "
                           "JOIN readings r ON r.id = p.reading_id JOIN stories s ON s.id = r.story_id "
                           "WHERE p.id = ?", (practice_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Practice not found")
    if not local_models.whisper_loaded():
        raise HTTPException(503, "Whisper is not loaded. Check /health.")
    targets = list(dict.fromkeys(db.from_json(row["red_words"])))[:3]

    webm = wav = None
    try:
        webm = _save_upload(audio)
        wav = to_wav(webm)
        words = check_reading(wav, " ".join(db.from_json(row["sentences"])), row["language"])
    except subprocess.CalledProcessError:
        raise HTTPException(400, "Could not read the recording. Please try again.")
    finally:
        _delete(webm, wav)

    # A target word is still missed if it was never read green in the practice sentences.
    read_ok = {normalize(w["word"]) for w in words if w["status"] == "green"}
    still_missed = [t for t in targets if t not in read_ok]
    with db.connect() as conn:
        conn.execute("UPDATE practice SET wrong_after = ?, still_missed = ? WHERE id = ?",
                     (len(still_missed), db.to_json(still_missed), practice_id))
    return {"words": words, "wrong_before": row["wrong_before"], "wrong_after": len(still_missed),
            "still_missed": still_missed}


# ---------- Teacher's Class View ----------

@app.get("/teacher/class")
def teacher_class():
    with db.connect() as conn:
        pupils = conn.execute("SELECT id, first_name, class_no, grade, latest_tip FROM pupils").fetchall()
        readings = conn.execute("SELECT id, pupil_id, read_at, seconds_taken, words_correct, total_words, "
                                "red_words FROM readings ORDER BY read_at").fetchall()
        missed = conn.execute("SELECT reading_id, still_missed FROM practice").fetchall()

    still_missed = {}
    for m in missed:
        still_missed.setdefault(m["reading_id"], []).extend(db.from_json(m["still_missed"]))
    by_pupil = {}
    for r in readings:
        by_pupil.setdefault(r["pupil_id"], []).append(r)

    result = []
    for p in pupils:
        last5 = by_pupil.get(p["id"], [])[-5:]  # oldest -> newest
        counts = Counter()
        for r in last5:  # trouble words = red words + words still missed after practice
            counts.update(db.from_json(r["red_words"]))
            counts.update(still_missed.get(r["id"], []))
        latest = last5[-1] if last5 else None
        result.append({
            "id": p["id"],
            "first_name": p["first_name"],
            "class_no": p["class_no"],
            "grade": p["grade"],
            "latest_accuracy": round(latest["words_correct"] / latest["total_words"], 2) if latest else None,
            "latest_words_correct": latest["words_correct"] if latest else None,
            "latest_total_words": latest["total_words"] if latest else None,
            "latest_seconds": latest["seconds_taken"] if latest else None,
            "trouble_words": [w for w, _ in counts.most_common(5)],
            "tip": p["latest_tip"],
            "last5": [round(r["words_correct"] / r["total_words"], 2) for r in last5],
            "last_read_at": latest["read_at"] if latest else None,
        })
    return result


# ---------- Frontend (mounted last so API routes win) ----------

app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
