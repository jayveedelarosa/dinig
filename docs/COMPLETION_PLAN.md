# Dinig — Completion Plan

_Last updated: 2026-10-10_

---

## Status summary

| Phase | What | Status |
|---|---|---|
| 1 | Backend: wire up Qwen (`generate()` + 4 callsites) | ✅ Done |
| 2 | Backend: replace placeholder stories | ✅ Done |
| 3a | Frontend: fix heatmap blank-cell ordering | ✅ Done |
| 3b | Frontend: fix My Result scroll on 1366×768 | ✅ Done |
| 3c | Frontend: fix Pick Your Name tile overflow (40 pupils) | ✅ Done |
| 4a–e | Frontend: wire Figma mockup to existing UI | 🔲 To do |
| 5 | Offline verification + demo prep | 🔲 To do |

---

## Phase 1 — Backend: wire up Qwen ✅

### What was done
Both files are complete and live in the repo.

**`backend/ai/local_models.py` — `generate()`**
Implemented as `POST {OLLAMA_URL}/api/generate` using `urllib.request.urlopen()` with a
`timeout` parameter. Parses `response["response"]` as JSON. Returns `None` on any exception
(timeout, bad JSON, Ollama not running). Callers always handle `None` with a fallback.

**`backend/main.py` — 4 callsites**

| Callsite | Route | AI call | Fallback |
|---|---|---|---|
| AI tip (background) | `POST /readings` | `_ai_tip_task()` via `BackgroundTasks` | `rule_based_tip()` stays if Qwen is slow |
| AI quiz questions | `GET /quiz/{reading_id}` | `generate()` with story text + Grade 3 prompt | 2 pre-written backup questions from DB |
| AI answer judging | `POST /quiz/answer` | `generate()` with story + question + heard answer | keyword match against backup answer |
| AI practice sentences | `POST /practice` | `generate()` with up to 3 missed words | template "I can read the word ___." |

`BackgroundTasks` is imported from `fastapi`. All four fallbacks are working and tested.

---

## Phase 2 — Backend: replace placeholder stories 🔲

**Files:** `backend/seed.py`

Write 3 real Grade 3/4 English stories set in a Filipino context (~50 words each).
Each story needs harder words so red words look realistic in the demo (e.g. "carabao",
"bridge", "careful", "bucket", "harvest"). Add 2 backup questions per story
(one "what happened", one "why"), each with a short answer.

Seed data shape needed per story:
```python
{
  "title": "...",
  "language": "en",
  "grade_level": 3,
  "full_text": "...",   # no [PLACEHOLDER STORY:] prefix
  "questions": [
    {"question": "...", "answer": "..."},
    {"question": "...", "answer": "..."},
  ],
}
```

After updating `seed.py`, run it to refresh the DB:
```
venv\Scripts\python.exe backend\seed.py
```

Verify with `GET /stories` and `GET /quiz/{reading_id}`.

---

## Phase 3 — Frontend: fix 3 known layout bugs 🔲

### 3a — Heatmap blank-cell ordering (`frontend/app.js`)

Blanks currently appear on the right (newest side). Must be on the left (oldest side)
so the newest reading is always the rightmost cell.

In `renderClass()`, replace the heat loop:
```js
const padded = Array(5 - p.last5.length).fill(undefined).concat(p.last5);
for (let i = 0; i < 5; i++) {
  const acc = padded[i];
  heat.appendChild(el("span", { class: `cell ${band(acc)}` },
    acc === undefined ? "–" : String(Math.round(acc * 100))));
}
```

### 3b — My Result scrolls off 1366×768 (`frontend/styles.css`)

The result word view uses the same 36px `.story` class as the read-aloud text.
Add a smaller override for the result:
```css
.story.result {
  font-size: 22px;
  line-height: 1.6;
}
```

### 3c — Pick Your Name overflows with 40 pupils (`frontend/styles.css`)

Reduce tile minimum size:
```css
.tiles { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.tile { min-height: 80px; font-size: 1.1em; }
```

---

## Phase 4 — Frontend: wire Figma mockup 🔲

### 4a — Export assets from Figma
- Dinig logo/wordmark → SVG (replace `<h1 class="logo">Dinig</h1>`)
- Story illustration images → for Pick a Story cards and Story Quiz header
- Mic, back arrow, star icons → SVG
- Exact spacing/padding values from each frame

### 4b — Screen-by-screen mapping

| Figma frame | HTML `<section>` id | Key changes expected |
|---|---|---|
| Home | `#home` | Logo graphic, button styling, badge placement |
| Pick Your Name | `#pick-name` | Tile grid layout, avatar/number display |
| Pick a Story | `#pick-story` | Story card with image/illustration |
| Read Aloud | `#read-aloud` | Story text layout, Start/Done button, mic animation |
| Checking | `#checking` | Loading animation style |
| My Result | `#my-result` | Word color display, score layout, Next button |
| Story Quiz | `#story-quiz` | Question display, Answer button, feedback |
| Practice Again | `#practice-again` | Sentence display, "Before/Now" result |
| All Done | `#all-done` | Stars, name, Next Reader button |
| Class View | `#class-view` | Table, heatmap, Add Pupil form, sort control |

### 4c — Update `styles.css` per Figma
Work screen by screen. CSS variables already match `docs/BRAND.md`. Changes will be:
- Spacing (padding, margins, gaps)
- Border-radius on cards/tiles
- Font sizes on specific elements
- Button shapes if Figma differs from current rounded rectangles
- Illustration/image placements

### 4d — Add real Dinig icon
Replace `<link rel="icon" href="data:,">` in `index.html` with the exported favicon.

### 4e — Add story title to Story Quiz
In `index.html`, add inside `#story-quiz` header:
```html
<span id="quiz-story-title" class="muted small"></span>
```
In `app.js`, update `onEnter["story-quiz"]`:
```js
onEnter["story-quiz"] = () => {
  $("#quiz-story-title").textContent = state.story?.title || "";
  showQuestion();
};
```

### 4f — Fix recording button color
The recording "Done" button currently uses the same red as practice words (confusing).
Coordinate with designer: use primary blue or a neutral color with a mic pulse indicator.

---

## Phase 5 — Offline verification and demo prep 🔲

### 5a — Create `.env` on demo laptop
```
copy .env.example .env
```
If the 8GB laptop is slow with `qwen2.5:3b`, set `OLLAMA_MODEL=qwen2.5:1.5b` in `.env`.

### 5b — Full demo flow: run 3× with Wi-Fi off
Success criteria (from PRD):
- [ ] `/health` → all 4 flags `true` (`whisper_loaded`, `ollama_ready`, `ffmpeg_found`, `db_ok`)
- [ ] Full pupil flow: Mika → story → read aloud → colored result → quiz → practice → all done
- [ ] Teacher view: Mika at top with score, trouble words, AI tip
- [ ] `temp/` folder empty after each run

### 5c — Measure actual speeds
Record on the demo laptop with Wi-Fi off:
- Done → word-colored result (Whisper time)
- Done → quiz question appears (Qwen first-response time)
- After reading → AI tip visible in Class View (background task time)

**Only publish numbers you actually measured.** Update `README.md` with real measurements.

### 5d — Warm-up Qwen at startup
`SYSTEM_DESIGN.md` notes that startup should send one tiny prompt to Qwen so the first
real request isn't slow. If not already done, add to the `lifespan()` function in `main.py`:
```python
# After load_whisper():
if local_models.ollama_ready():
    local_models.generate("ping", timeout=30)  # warm up; response ignored
```

---

## Priority order

| # | Task | Owner | Blocks |
|---|---|---|---|
| 1 | Write 3 real stories + questions → `seed.py` | Designer writes; Backend codes | Demo realism |
| 2 | Fix heatmap cell ordering (3a) | Frontend | Demo accuracy |
| 3 | Fix My Result scroll (3b) | Frontend | Demo on 1366×768 |
| 4 | Fix Pick Your Name tile size (3c) | Frontend | Demo with 40 pupils |
| 5 | Wire Figma: Home screen | Frontend | First impression |
| 6 | Wire Figma: My Result | Frontend | Wow moment |
| 7 | Wire Figma: remaining pupil screens | Frontend | Polish |
| 8 | Wire Figma: Class View | Frontend | Teacher demo |
| 9 | Add story title to Story Quiz (4e) | Frontend | Minor polish |
| 10 | Fix recording button color (4f) | Frontend + Designer | Minor polish |
| 11 | Add Qwen warm-up at startup (5d) | Backend | First-run speed |
| 12 | Create `.env` on demo laptop (5a) | Everyone | Offline demo |
| 13 | Measure speeds, update README (5c) | Backend | Submission accuracy |
| 14 | Full 3× offline demo run (5b) | Everyone | Go/no-go |

---

## What does NOT need to be touched

- `backend/ai/local_models.py` — `generate()` fully implemented ✅
- `backend/main.py` — all 4 AI callsites wired with fallbacks ✅
- `backend/reading_check.py` — Plan A working ✅
- `backend/audio.py` — fully working ✅
- `backend/db.py` — fully working ✅
- `backend/tips.py` — rule-based fallback working ✅
- `start_dinig.bat` — correct ✅
- `requirements.txt` — no new packages needed ✅
