"""One-time setup (needs internet): download Whisper small for faster-whisper.

Run from the project folder:
    venv\\Scripts\\python.exe backend\\download_models.py

After this, Dinig loads Whisper from models\\faster-whisper-small with no internet.
Qwen is downloaded separately with: ollama pull qwen2.5:3b

Plain HTTP with resume: if the internet drops, run it again and it continues
where it stopped (school internet is often slow or unstable).
"""
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = {
    # name: (Hugging Face repo, local folder)
    "small": ("Systran/faster-whisper-small", ROOT / "models" / "faster-whisper-small"),
    "tiny.en": ("Systran/faster-whisper-tiny.en", ROOT / "models" / "faster-whisper-tiny.en"),  # dev testing only
}
FILES = ["config.json", "tokenizer.json", "vocabulary.txt", "model.bin"]


def download(url: str, dest: Path) -> None:
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0
    req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
    with urllib.request.urlopen(req, timeout=60) as resp:
        if have and resp.status != 206:  # server ignored the resume request: start over
            have = 0
        total = have + int(resp.headers.get("Content-Length", 0))
        with open(part, "ab" if have else "wb") as f:
            done = have
            while chunk := resp.read(1 << 16):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {dest.name}: {done / 1e6:.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    part.replace(dest)
    print()


def main(name: str = "small") -> None:
    repo, target = MODELS[name]
    target.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {repo} to {target}")
    for fname in FILES:
        dest = target / fname
        if dest.exists():
            print(f"  {fname}: already downloaded")
            continue
        download(f"https://huggingface.co/{repo}/resolve/main/{fname}", dest)
    print("Done. Whisper is ready for offline use.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "small")
