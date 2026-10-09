"""One-time setup (needs internet): download Whisper small for faster-whisper.

Run from the project folder:
    venv\\Scripts\\python.exe backend\\download_models.py

After this, Dinig loads Whisper from models\\faster-whisper-small with no internet.
Qwen is downloaded separately with: ollama pull qwen2.5:3b
"""
import os
from pathlib import Path

os.environ.pop("HF_HUB_OFFLINE", None)  # this script is the one place allowed online

from huggingface_hub import snapshot_download  # noqa: E402  (installed with faster-whisper)

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "models" / "faster-whisper-small"

if __name__ == "__main__":
    print(f"Downloading Systran/faster-whisper-small to {TARGET} ...")
    snapshot_download(repo_id="Systran/faster-whisper-small", local_dir=str(TARGET))
    print("Done. Whisper small is ready for offline use.")
