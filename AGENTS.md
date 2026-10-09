# Agent rules

## Project in one sentence
Grade 3 and 4 public school pupils struggle to read simple texts because no one has time to listen to each of them read aloud. We solve it with Dinig: pupils read aloud to a shared Windows laptop, local AI checks every word and their understanding, and the teacher (or a parent at home) gets a one-screen class view with a tip per pupil, all with Wi-Fi off. [CHANGED]

## Hackathon theme: LOCAL AI (most important rule)
- The core AI must run on the user's device. Never use a cloud AI API (OpenAI, Claude API, Gemini API) for core features.
- The core features must keep working with the internet turned off.
- Cloud services are allowed only as secondary parts (for example a database or a non-AI API).
- Never invent or exaggerate speed numbers. Only report numbers we actually measured.

## Read first
Always read docs/index.md before starting any task. Only open the docs it says are relevant.

## Tech stack (do not change without asking)
- Frontend: plain HTML, CSS and JavaScript (no build step), served by FastAPI; MediaRecorder for the mic. Desktop app: start_dinig.bat starts the server and opens Microsoft Edge in app mode (msedge --app=http://localhost:8000), so there are no tabs or address bar. [CHANGED]
- Backend: Python + FastAPI
- Database: SQLite (one file, data/dinig.db)
- Local AI runtime: Ollama (language model) and faster-whisper with compute_type "int8" (speech to text, loaded once at startup); ffmpeg for audio conversion [CHANGED]
- Local AI model(s): qwen2.5:3b (about 1.9GB, default) with qwen2.5:1.5b as a fallback set in .env, and Whisper small (about 470MB) [CHANGED]
- Package manager: pip (backend only; no npm)
- OS: team uses Windows. All commands must work in Windows terminal.
- Demo laptop: OPEN QUESTION (model, RAM, processor). Minimum target: 8GB RAM Windows laptop (typical DepEd laptop), no graphics card. Fully offline, no phone needed. [CHANGED]

## Rules
- Build only the core features in docs/PRD.md. Ask before adding anything else.
- All AI calls go through one module (for example ai/localModel). Nothing else talks to the model directly.
- Show a short plan before big changes.
- Small commits with clear messages.
- Never put API keys or passwords in code. Use .env.
- Keep code simple enough that a teammate can explain it to a judge. Add short comments to tricky parts.
- When a task is done, update the matching doc if anything changed.

## Team
- [Name], leader: docs, skeleton, frontend build, README
- [Name], backend: server, database, local AI model setup
- [Name], designer: screens in Figma/Canva, slides
- [Name], pitcher: research, slides, video, post
