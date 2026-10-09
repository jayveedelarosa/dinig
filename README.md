# Dinig
Grade 3 and 4 public school pupils struggle to read simple texts because no one has time to listen to each of them read aloud. Dinig listens to each pupil read a short story on the classroom laptop, highlights missed words, checks understanding, and gives the teacher (or a parent at home) a one-screen class view, all with Wi-Fi off.

## Why does this product benefit from running AI locally?
- **Privacy:** recordings of children's voices are scored on the laptop and deleted right after. Only scores, times and trouble words are saved.
- **Offline:** almost 12,000 public schools have no internet (SONA 2025, via The Post). Dinig needs no internet, no phone and no account after setup.
- **Cost:** no per-use cloud fees. It runs on the 8GB laptops schools and families already have.
- **Impossible with cloud:** for a school with no internet, a cloud version simply does not work.

## Demo
[1-minute video link] · [X or LinkedIn post link] · [screenshots]

## Features
1. **Read and Check (with Timer):** the child reads aloud; every word turns green (correct), red (practice word) or grey (skipped), with a score and reading time.
2. **Teacher's Class View (with Heatmap):** every pupil's latest score, time, trouble words and a tip; a heatmap of the last 5 readings.
3. **Story Quiz:** 2 questions about the story, answered out loud.
4. **Practice Again:** short sentences with the child's practice words, then "Before / Now".

## What runs locally
- [x] Speech to text: Whisper small (faster-whisper, int8, CPU)
- [x] Language AI: Qwen2.5 3B via Ollama (fallback: Qwen2.5 1.5B)
- [x] Reading check (Whisper + Python difflib), audio conversion (ffmpeg), FastAPI server, SQLite database, the app window (Edge app mode)

## What requires internet
- Nothing. The app works fully offline. Internet is only needed **once**, during setup, to download Python packages and the models.

---

## Set up on a fresh Windows laptop (step by step)
Minimum laptop: **8GB RAM**, Windows 10 or 11, no graphics card needed. About 4GB of free disk space.
Do all of this **with internet**, the day before. After that, Dinig runs with Wi-Fi off.

### 1. Install the tools (once)
1. **Python 3.12** (recommended; the demo laptop uses 3.12): download "Windows installer (64-bit)" from https://www.python.org/downloads/release/python-31210/ (3.12.10 is the last 3.12 release with a Windows installer).
   On the first installer screen, **tick "Add python.exe to PATH"**, then click Install Now.
2. **Git**: https://git-scm.com/download/win (default options are fine).
3. **Ollama** (runs Qwen locally): https://ollama.com/download/windows. Install it; it starts by itself in the system tray.
4. **Microsoft Edge** is already on Windows. Nothing to install.

Check in a new **Command Prompt** (Start menu, type `cmd`):
```
py -3.12 --version
git --version
ollama --version
```

### 2. Get the code
```
cd %USERPROFILE%\Desktop
git clone [repo link] dinig
cd dinig
```

### 3. Create the Python environment and install packages
```
py -3.12 -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
```
ffmpeg comes inside the `imageio-ffmpeg` package, so you do not need to install ffmpeg separately.

### 4. Download the models (once, about 2.5GB total)
```
venv\Scripts\python.exe backend\download_models.py
ollama pull qwen2.5:3b
ollama pull qwen2.5:1.5b
```
- Whisper small (about 470MB) goes to `models\faster-whisper-small`.
- Qwen2.5 3B (about 1.9GB) is the default. Qwen2.5 1.5B is the fallback for slow or full 8GB laptops.
- **Developer laptop with less than 8GB RAM (not for the demo):** download the tiny English model instead with `venv\Scripts\python.exe backend\download_models.py tiny.en`, and in `.env` set `WHISPER_MODEL_DIR=models/faster-whisper-tiny.en`. It is less accurate; the demo always uses small.

### 5. Settings and sample data
```
copy .env.example .env
venv\Scripts\python.exe backend\seed.py
```
`seed.py` resets the database and loads the **sample class** (10 made-up pupils with past results, demo pupil "Mika", 3 placeholder stories). Run it again any time to reset before a demo.

### 6. Start Dinig
Double-click **`start_dinig.bat`**. It starts the server (minimized window "Dinig server") and opens Dinig in its own Edge window.
- **First time only:** Edge asks to use the microphone. Click **Allow**. Do this during setup, not on stage.
- To stop Dinig: close the Dinig window, then close the minimized "Dinig server" window.

### 7. Test offline (do this before every demo)
1. Turn **Wi-Fi off**.
2. Double-click `start_dinig.bat`.
3. Home shows a status line. It should say **"Ready: all local AI loaded"** (or open http://localhost:8000/health in Edge: `whisper_loaded`, `ollama_ready`, `ffmpeg_found` and `db_ok` should all be `true`).
4. Tap **I'm a Pupil**, pick **Mika**, pick a story, tap **Start**, read aloud, tap **Done**. Words turn green, red or grey.
5. Tap **Teacher / Parent**: Mika is at the top of the Class View.
6. Check the `temp` folder is empty (audio is deleted after scoring).

### Troubleshooting
| Problem | Fix |
| --- | --- |
| "venv\Scripts\python.exe was not found" | Step 3 was skipped. Run it in the `dinig` folder. |
| Whisper download is slow or stopped | Run `venv\Scripts\python.exe backend\download_models.py` again: it resumes where it stopped. It shows MB downloaded so far. |
| Status says "Missing: Whisper" | Run `venv\Scripts\python.exe backend\download_models.py` (with internet), then restart. |
| Status says "Qwen not running" | Open Ollama from the Start menu, and check `ollama list` shows `qwen2.5:3b` (or the model in `.env`). Reading still works; quiz and tips use pre-written backups. |
| Qwen is very slow or the laptop freezes | In `.env` set `OLLAMA_MODEL=qwen2.5:1.5b`, close both Dinig windows, start again. |
| Microphone does not work | Edge window menu (…) > Settings > Cookies and site permissions > Microphone: allow `localhost:8000`. Check Windows Settings > Privacy > Microphone is on. Always open Dinig through `localhost`, not an IP address. |
| "Dinig did not start" / port 8000 in use | Close any old "Dinig server" window and try again. If still stuck: `netstat -ano | findstr :8000`, then `taskkill /PID <number> /F`. |
| Want a clean demo | `venv\Scripts\python.exe backend\seed.py` |

For developers, run the server with live reload instead of the launcher, and run the reading check tests:
```
venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
venv\Scripts\python.exe tests\test_reading_check.py
```

Minimum laptop: 8GB RAM, no graphics card. Tested on: OPEN QUESTION (demo laptop not chosen yet). Speed: OPEN QUESTION until measured on the demo laptop.

---

## Disclosures
- **Models used:**
  - Whisper small, converted for faster-whisper: https://huggingface.co/Systran/faster-whisper-small (MIT license, original model by OpenAI)
  - Qwen2.5 3B Instruct and Qwen2.5 1.5B Instruct via Ollama: https://ollama.com/library/qwen2.5 (Qwen2.5 3B: Qwen Research License; Qwen2.5 1.5B: Apache 2.0)
- **Technologies and frameworks:** Python, FastAPI, Uvicorn, faster-whisper (CTranslate2), Ollama, SQLite, ffmpeg (via imageio-ffmpeg), plain HTML/CSS/JavaScript, Microsoft Edge app mode
- **Fonts:** Nunito (The Nunito Project Authors), Andika (SIL International) and Atkinson Hyperlegible (Braille Institute), all SIL Open Font License, bundled in `frontend/fonts/`
- **APIs and cloud services:** None.
- **Existing code and assets:** None. Built during the hackathon.
- **AI development tools:** Claude Code (planning docs and code scaffolding), Figma Make (UI design). [add others the team used]
