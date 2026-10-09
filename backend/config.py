"""Settings from .env (see .env.example). Every setting has a safe default."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Never let Hugging Face reach the internet at runtime. The Whisper model is
# loaded from a local folder (downloaded once by backend/download_models.py).
os.environ.setdefault("HF_HUB_OFFLINE", "1")


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


DB_PATH = _path(os.getenv("DB_PATH", "data/dinig.db"))
TEMP_DIR = _path(os.getenv("TEMP_DIR", "temp"))
FRONTEND_DIR = ROOT / "frontend"

WHISPER_MODEL_DIR = _path(os.getenv("WHISPER_MODEL_DIR", "models/faster-whisper-small"))
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_CPU_THREADS = int(os.getenv("WHISPER_CPU_THREADS", "0"))  # 0 = let faster-whisper decide

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")  # fallback for 8GB laptops: qwen2.5:1.5b

READING_CHECK = os.getenv("READING_CHECK", "plan_a")
QUIZ_TIMEOUT_SECONDS = float(os.getenv("QUIZ_TIMEOUT_SECONDS", "8"))
