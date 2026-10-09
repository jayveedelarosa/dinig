"""Audio conversion with ffmpeg: browser .webm -> 16kHz mono .wav (what Whisper needs)."""
import shutil
import subprocess
from pathlib import Path


def ffmpeg_exe() -> str | None:
    """Use ffmpeg from PATH if installed, else the copy bundled with the imageio-ffmpeg pip package."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def to_wav(src: Path) -> Path:
    exe = ffmpeg_exe()
    if not exe:
        raise RuntimeError("ffmpeg not found. Run: venv\\Scripts\\python.exe -m pip install imageio-ffmpeg")
    dst = src.with_suffix(".wav")
    subprocess.run(
        [exe, "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst)],
        check=True,
        capture_output=True,
    )
    return dst
