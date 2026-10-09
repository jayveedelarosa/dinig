"""Dinig backend: FastAPI on http://localhost:8000. Serves the API and the frontend.

Start it with start_dinig.bat (or for development):
    venv\\Scripts\\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
"""
import logging
import shutil
import subprocess
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import config, db
from backend.ai import local_models
from backend.audio import ffmpeg_exe, to_wav
from backend.reading_check import check_reading, summarize
from backend.text_utils import clean_story
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


@app.post("/readings")
def create_reading(
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
    # TODO [BACKEND]: start the AI tip in a BackgroundTasks job (local_models.generate);
    # it replaces the rule-based tip when ready.

    return {"reading_id": reading_id, "words": words, "words_correct": s["words_correct"],
            "total_words": s["total_words"], "seconds_taken": seconds}


# ---------- Frontend (mounted last so API routes win) ----------

app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
