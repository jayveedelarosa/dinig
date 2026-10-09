"""The ONLY module that talks to the local AI models (AGENTS.md rule).

- Whisper small (faster-whisper, int8, CPU): loaded ONCE at server startup.
- Qwen2.5 via Ollama on localhost: model name comes from OLLAMA_MODEL in .env.
Nothing here ever calls a cloud API.
"""
import json
import logging
import urllib.request

from backend import config

log = logging.getLogger("dinig.models")

_whisper = None  # set once by load_whisper()


def load_whisper() -> bool:
    """Load Whisper from its local folder. Called once at startup; never per request."""
    global _whisper
    if _whisper is not None:
        return True
    if not (config.WHISPER_MODEL_DIR / "model.bin").exists():
        log.error("Whisper model not found in %s. Run: venv\\Scripts\\python.exe backend\\download_models.py",
                  config.WHISPER_MODEL_DIR)
        return False
    try:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel(
            str(config.WHISPER_MODEL_DIR),
            device="cpu",
            compute_type=config.WHISPER_COMPUTE_TYPE,  # int8 keeps memory low on 8GB laptops
            cpu_threads=config.WHISPER_CPU_THREADS,
        )
        log.info("Whisper loaded from %s (%s)", config.WHISPER_MODEL_DIR, config.WHISPER_COMPUTE_TYPE)
        return True
    except Exception:
        log.exception("Could not load Whisper")
        return False


def whisper_loaded() -> bool:
    return _whisper is not None


def transcribe(wav_path, language: str = "en") -> str:
    """Speech to text. We never pass the story text as a prompt, so Whisper
    is less likely to "autocorrect" a misread word into the right one."""
    if _whisper is None:
        raise RuntimeError("Whisper is not loaded")
    if not _whisper.model.is_multilingual:
        language = None  # English-only model (tiny.en on the dev laptop)
    elif language == "fil":
        language = "tl"  # Whisper's code for Tagalog/Filipino
    segments, _info = _whisper.transcribe(
        _read_wav(wav_path),
        language=language,
        beam_size=1,  # faster on CPU; tune after measuring on the demo laptop
        condition_on_previous_text=False,
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


def _read_wav(wav_path):
    """Read the 16kHz mono 16-bit .wav that ffmpeg made, as float32 samples.
    We pass samples instead of a file path so faster-whisper skips its own
    PyAV decoding (PyAV version changes broke it once)."""
    import wave

    import numpy as np  # installed with faster-whisper
    with wave.open(str(wav_path), "rb") as w:
        frames = w.readframes(w.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def ollama_ready() -> bool:
    """True if Ollama is running locally and has OLLAMA_MODEL pulled."""
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_URL}/api/tags", timeout=2) as resp:
            names = [m.get("name", "") for m in json.load(resp).get("models", [])]
        return config.OLLAMA_MODEL in names
    except Exception:
        return False


def generate(prompt: str, timeout: float) -> str | None:
    """Ask Qwen (via local Ollama) for text. Returns None if slow or failing,
    so callers use their pre-written fallback.

    TODO [BACKEND]: implement with POST {OLLAMA_URL}/api/generate
      body: {"model": OLLAMA_MODEL, "prompt": prompt, "stream": false,
             "format": "json", "keep_alive": "30m"}
    Use `timeout`; on timeout or bad JSON return None. Used for quiz
    questions, answer judging, practice sentences and pupil tips.
    """
    return None
