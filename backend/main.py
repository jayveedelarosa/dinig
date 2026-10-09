"""Dinig backend: FastAPI on http://localhost:8000. Serves the API and the frontend.

Start it with start_dinig.bat (or for development):
    venv\\Scripts\\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import config, db
from backend.ai import local_models
from backend.audio import ffmpeg_exe
from backend.text_utils import clean_story

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


# ---------- Frontend (mounted last so API routes win) ----------

app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
