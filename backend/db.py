"""SQLite database: one file (data/dinig.db). Tables match docs/SYSTEM_DESIGN.md.

JSON lists (red_words, skipped_words, sentences, still_missed) are stored as TEXT.
"""
import json
import sqlite3
from contextlib import contextmanager

from backend.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS pupils (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name  TEXT NOT NULL,
    class_no    TEXT,
    grade       INTEGER NOT NULL,
    latest_tip  TEXT
);
CREATE TABLE IF NOT EXISTS stories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    language    TEXT NOT NULL DEFAULT 'en',
    full_text   TEXT NOT NULL,
    grade_level INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS questions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id    INTEGER NOT NULL REFERENCES stories(id),
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS readings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pupil_id      INTEGER NOT NULL REFERENCES pupils(id),
    story_id      INTEGER NOT NULL REFERENCES stories(id),
    read_at       TEXT NOT NULL,
    seconds_taken INTEGER NOT NULL,
    words_correct INTEGER NOT NULL,
    total_words   INTEGER NOT NULL,
    red_words     TEXT NOT NULL DEFAULT '[]',
    skipped_words TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS practice (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_id   INTEGER NOT NULL REFERENCES readings(id),
    sentences    TEXT NOT NULL DEFAULT '[]',
    wrong_before INTEGER NOT NULL,
    wrong_after  INTEGER,
    still_missed TEXT NOT NULL DEFAULT '[]'
);
-- Privacy rule: we store only the result, never what the child said.
CREATE TABLE IF NOT EXISTS quiz_answers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_id  INTEGER NOT NULL REFERENCES readings(id),
    question    TEXT NOT NULL,
    result      TEXT NOT NULL CHECK (result IN ('right', 'wrong', 'unchecked'))
);
"""


@contextmanager
def connect():
    """`with connect() as conn:` commits on success, rolls back on error, always closes."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def db_ok() -> bool:
    try:
        with connect() as conn:
            conn.execute("SELECT 1 FROM pupils LIMIT 1")
        return True
    except sqlite3.Error:
        return False


def to_json(items) -> str:
    return json.dumps(list(items))


def from_json(text) -> list:
    return json.loads(text) if text else []
