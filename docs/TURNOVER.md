# Dinig — Developer Turnover for Cursor
_Last updated: 2026-10-10 01:34 PHT_

---

## Project in one sentence
Dinig is a plain HTML/CSS/JS + Python/FastAPI desktop app (Edge app mode, no internet after setup) that listens to Grade 3–4 pupils read aloud, colors every word green/red/grey, and gives the teacher a one-screen class view with AI tips — all powered by local Whisper + Qwen via Ollama, fully offline.

---

## Current state: what is DONE

| Phase | Status | Evidence |
|---|---|---|
| Phase 1 — Qwen `generate()` + 4 AI callsites wired | ✅ Complete | 30/30 tests pass in `tests/test_phase1.py` |
| Phase 2 — Real stories in seed.py (no placeholders) | ✅ Complete | 3 stories × 56–62 words, 6 backup questions, no `[PLACEHOLDER]` text |
| Phase 3a — Heatmap blank-cell ordering fixed | ✅ Complete | 29/29 tests pass in `tests/test_phase3_frontend.js` |
| Phase 3b — My Result font override for 1366×768 | ✅ Complete | `.story.result { font-size:22px; line-height:1.6 }` in styles.css |
| Phase 3c — Pick Your Name tile size (40 pupils) | ✅ Complete | minmax(140px), min-height 80px |
| Phase 4 — Figma mockup wiring | ✅ Complete (2026-10-10) — styles.css rewritten from the Make CSS, app.js wired, Nunito + Inter bundled; all screens fit 1366×768 (checked with headless Chrome) |

**Total passing tests:** 10 (reading check) + 30 (Phase 1) + 29 (Phase 3 frontend) = **69 tests**

Run all:
```
venv/bin/python tests/test_reading_check.py
venv/bin/python tests/test_phase1.py
node tests/test_phase3_frontend.js
```

---

## Phase 4 status — what was done and what remains

### What was completed before handover

1. **Assets extracted and copied** — `frontend/assets/` now contains:
   - `logo.svg` — Dinig wordmark (green rounded rect with "DINIG" text in white, ~74×48 display)
   - `logo-alt.svg` — alternate version
   - `mascot/dindin-expression-grid.png` — 1200×1600 sprite sheet, 3 cols × 4 rows = 12 expressions
   - `mascot/dindin-primary.jpg` — standalone mascot photo
   - `mascot/dindin-expressions.jpg` — expressions reference

2. **`frontend/index.html` rewritten** — fully updated with:
   - Logo `<img>` in every screen header
   - Animated SVG elephant (ElephantIdle, inline in Home screen)
   - Step progress bar in every pupil screen header (`Step N of 8`)
   - Offline pill in every header
   - Role cards with icons on Home screen
   - Eyebrow labels on all screens
   - Mascot `dindin-expression` divs on every screen (read-aloud, checking, result, quiz, practice, all-done)
   - New semantic HTML structure matching Figma layout

### What still needs to be done

#### 3. `frontend/styles.css` — NEEDS FULL REWRITE
The current `styles.css` still uses the old color tokens. It needs to be replaced with the Figma design system.

**Design tokens from Figma (use these exactly):**
```css
:root {
  --green:      #00a460;
  --green-dark: #008750;
  --green-soft: #e9f8f1;
  --blue:       #1cb0f6;
  --blue-dark:  #138bc4;
  --blue-soft:  #eaf7fe;
  --yellow:     #ffc800;
  --yellow-soft:#fff7d5;
  --red:        #ff4b4b;
  --ink:        #303a36;
  --muted:      #61706a;
  --subtle:     #8a9792;
  --line:       #dce7e2;
  --surface:    #ffffff;
  --canvas:     #f6f9f7;
  --navy:       #263b63;
  --shadow:     0 12px 36px rgba(37,65,54,.08);
}
```

**Fonts:** Nunito (headings, buttons — weight 700/900) + Inter (body). Both need to be bundled in `frontend/fonts/` — **no Google Fonts CDN** (app must work offline). Add:
- `Nunito-Regular.ttf`, `Nunito-Bold.ttf`, `Nunito-ExtraBold.ttf`
- `Inter-Regular.ttf`, `Inter-Medium.ttf`

Or fall back to Andika (already bundled) for pupil mode and Atkinson Hyperlegible for teacher mode if Nunito/Inter can't be added in time.

**The full CSS to implement** is in the Figma make export at:
`/tmp/dinig_make/make_repos_extracted/` (git repo, commit `6acbab0`)

Read the full CSS with:
```bash
cd /tmp/dinig_figma_repo
git cat-file blob 75fba6ffc048862b107c764d603f700cb3b1c2ac
```

Key component styles needed (map from Figma CSS to plain CSS, no Tailwind):
- `.topbar` — 72px height, grid 3-col (logo | stepper | actions), border-bottom, white bg
- `.home-hero` — 2-col grid, mascot card on right with rounded border + gradient bg
- `.home-topbar` — same as topbar but 2-col (logo | actions)
- `.role-card` — white card, 3-col grid (icon | text | arrow), rounded-22px, box-shadow bottom
- `.offline-pill` — green pill with pulsing dot
- `.offline-badge` — yellow-soft bg badge at bottom of home
- `.eyebrow` — uppercase, green, small, letter-spaced
- `.stepper` — progress bar with green fill
- `.brand` — logo button
- `.btn`, `.btn-green`, `.btn-blue`, `.btn-quiet` — rounded-16px, min-height 52px, bottom shadow ("lift")
- `.dindin-expression` — sprite sheet positioning (see below)
- `.ele-wrap` — elephant animation container (already inline in HTML)
- `.mascot-speech` — speech bubble card (position: absolute, top-left of mascot card)
- `.sun-shape` — yellow circle (position: absolute, top-right of mascot card)
- `.name-grid` — 3-col grid of name tiles
- `.name-tile` — white card with initials avatar, name, arrow
- `.story-choice-grid` — 3-col grid of story cards
- `.story-choice-card` — card with colored art area + copy
- `.reader-layout` / `.quiz-layout` — 2-col: main card + buddy aside
- `.reading-card` / `.quiz-card` — white card, padding 34px 42px, shadow
- `.reading-passage` — Nunito, 36–42px, line-height 1.72
- `.reader-buddy` / `.quiz-mascot` — rounded card, gradient green→yellow bg
- `.result-page` — centered, max-width 1120px
- `.word-result-card` — white card for colored words
- `.marked-passage` — flex-wrap word spans
- `.correct-word` / `.practice-word` / `.skipped-word` — colored word spans with inset bottom shadow
- `.word-legend` — colored dots legend
- `.center-stage` — flex column center for checking/all-done
- `.loading-dots` — 3 bouncing green dots
- `.checking-mascot` — 280px container
- `.complete-stage` — with celebration-lines
- `.complete-stats` — 2-col stats grid
- `.class-page` — teacher view layout
- `.class-table-card` — white card with table
- `table th/td` — compact teacher table
- `.support-label` — colored status badges (on-track/needs-help/keep-eye)
- `.practice-layout` — practice page
- `.practice-sentences p` — Nunito 30px, white card, yellow highlight for `mark`
- `.practice-change` — before/after box

**Dindin expression sprite positions** (1200×1600 grid, 3 cols × 4 rows, each cell 400×400):
```css
.dindin-expression {
  width: 270px; aspect-ratio: 1;
  background-image: url("assets/mascot/dindin-expression-grid.png");
  background-repeat: no-repeat;
  background-size: 300% 400%;
  animation: expression-in 420ms cubic-bezier(.2,.85,.35,1) both,
             expression-idle 3.8s ease-in-out 500ms infinite;
  transform-origin: 50% 90%;
}
/* Row 1: encouraging(col1), waving(col2 — actually col1 row0=encouraging) */
/* Grid layout based on Figma CSS: */
.dindin-encouraging  { background-position: 50% 0; }
.dindin-waving       { background-position: 0 66.666%; }
.dindin-celebrating  { background-position: 50% 66.666%; }
.dindin-thinking     { background-position: 100% 66.666%; }
.dindin-retry        { background-position: 0 100%; }
.dindin-reading      { background-position: 50% 100%; }
@keyframes expression-in {
  from { opacity:0; transform:translateY(14px) scale(.94); }
  to   { opacity:1; transform:translateY(0) scale(1); }
}
@keyframes expression-idle {
  0%,100% { transform:translateY(0) rotate(-.5deg); }
  50%     { transform:translateY(-6px) rotate(.5deg); }
}
```

#### 4. `frontend/app.js` — NEEDS UPDATES
The existing `app.js` logic is fully functional. These additions are needed:

**a) Story title in quiz header** — add to `onEnter["story-quiz"]`:
```js
onEnter["story-quiz"] = () => {
  const eyebrow = document.getElementById("quiz-eyebrow");
  if (eyebrow && state.story) eyebrow.textContent = `${state.story.title} · Question 1 of 2`;
  showQuestion();
};
```

**b) Quiz mascot mood swap** — when answer is shown, change mascot from `dindin-thinking` to `dindin-encouraging`:
```js
// In the quiz answer handler, after showing feedback:
const qMascot = document.getElementById("quiz-mascot");
if (qMascot) {
  qMascot.classList.remove("dindin-thinking");
  qMascot.classList.add("dindin-encouraging");
}
```
Reset on next question:
```js
// When showing a new question:
if (qMascot) {
  qMascot.classList.remove("dindin-encouraging");
  qMascot.classList.add("dindin-thinking");
}
```

**c) Read Aloud helper text update** — when recording starts, update the prompt text:
```js
// After mic.start() succeeds in the Start button handler:
const helpMain = document.getElementById("read-help-main");
const promptMain = document.getElementById("read-prompt-main");
const promptSub = document.getElementById("read-prompt-sub");
if (helpMain) helpMain.textContent = "Dindin is listening";
if (promptMain) promptMain.textContent = "Take your time.";
if (promptSub) promptSub.textContent = "Tap Done only when you finish the whole story.";
```
Reset in `resetReadAloud()`:
```js
if (helpMain) helpMain.innerHTML = `Ready, <span class="pupil-name">${state.pupil?.first_name || ""}</span>?`;
if (promptMain) promptMain.textContent = "Read when you're ready.";
if (promptSub) promptSub.textContent = "The words will be checked after you finish.";
```

**d) My Result: populate done-score for All Done screen** — at the end of `onEnter["my-result"]`:
```js
const doneScore = document.getElementById("done-score");
if (doneScore) doneScore.textContent = `${r.words_correct} / ${r.total_words}`;
```

**e) My Result: update cheer message** — replace `kindMessage()` usage:
```js
// In onEnter["my-result"]:
document.getElementById("result-score").textContent = `${r.words_correct} of ${r.total_words} words correct`;
document.getElementById("result-message").textContent = "Nice reading! Here is what Dindin heard.";
document.getElementById("result-cheer").textContent = kindMessage(r.words_correct, r.total_words);
```

**f) My Result: word rendering** — update to use new CSS classes:
```js
r.words.forEach((w) => {
  const span = el("span", {
    class: w.status === "green" ? "correct-word"
         : w.status === "red"   ? "practice-word"
         :                        "skipped-word"
  }, w.word);
  box.appendChild(span);
  box.appendChild(document.createTextNode(" "));
});
```

**g) Practice result display** — update `onEnter["practice-again"]` to show the before/after box:
```js
// After practice result comes back, show practice-result-box:
document.getElementById("practice-result-box").classList.remove("hidden");
document.getElementById("practice-before").textContent = `${r.wrong_before} wrong word${r.wrong_before===1?"":"s"}`;
document.getElementById("practice-after").textContent  = `${r.wrong_after} wrong word${r.wrong_after===1?"":"s"}`;
```

**h) Navigation cleanup** — the old `#read-back` click listener pointed to `pick-story`. In the new HTML, the brand button in read-aloud already triggers `data-go` via the global click handler, BUT `#read-back` is the brand button id. Keep the existing listener:
```js
document.getElementById("read-back").addEventListener("click", () => {
  mic.cancel(); resetReadAloud(); go("pick-story");
});
```

**i) `go()` function** — add mascot mood reset per screen:
```js
// After the existing go() body, add:
const mascotMoods = {
  "read-aloud": ["dindin-reading"],
  "checking":   ["dindin-thinking"],
  "my-result":  ["dindin-encouraging"],
  "story-quiz": ["dindin-thinking"],
  "practice-again": ["dindin-retry"],
  "all-done":   ["dindin-celebrating"],
};
```

**j) Name tiles** — update `onEnter["pick-name"]` to use the new `.name-tile` class structure:
```js
const tile = document.createElement("button");
tile.className = "name-tile";
const initials = p.first_name.split(" ").map(w => w[0]).join("").slice(0,2).toUpperCase();
tile.innerHTML = `<span>${initials}</span><strong>${p.first_name}</strong>` +
  `<svg ... arrow icon svg ...></svg>`;
```

**k) Story cards** — update `onEnter["pick-story"]` to use `.story-choice-card` structure:
```js
tile.className = "story-choice-card";
tile.innerHTML = `
  <span class="story-art story-art-${idx===0?'meadow':idx===1?'seed':'rain'}">
    <svg ...book icon...></svg><i></i>
  </span>
  <span class="story-card-copy">
    <small>Grade ${s.grade_level}</small>
    <strong>${s.title}</strong>
  </span>
  <span class="story-go"><svg ...arrow icon...></svg></span>`;
```

---

## Files modified so far in Phase 4

| File | Status |
|---|---|
| `frontend/assets/logo.svg` | ✅ Created |
| `frontend/assets/logo-alt.svg` | ✅ Created |
| `frontend/assets/mascot/dindin-expression-grid.png` | ✅ Created |
| `frontend/assets/mascot/dindin-primary.jpg` | ✅ Created |
| `frontend/assets/mascot/dindin-expressions.jpg` | ✅ Created |
| `frontend/index.html` | ✅ Rewritten (557 lines) |
| `frontend/styles.css` | ✅ Rewritten (Make design tokens/components in plain CSS; compact `.tiles` mode when >9 pupils) |
| `frontend/app.js` | ✅ Updated (items a–k above, plus class summary + support labels) |
| `frontend/fonts/Nunito-Variable.ttf`, `Inter-Variable.ttf` | ✅ Added (OFL licenses included) |

Known design-asset note: `dindin-expression-grid.png` has an off-white (not transparent) background, so a faint square shows behind Dindin on plain backgrounds. Fix by re-exporting the sprite sheet with a transparent background from Figma.

---

## Files NOT to touch (fully done)

- `backend/ai/local_models.py` — `generate()` complete
- `backend/main.py` — all 4 AI callsites wired
- `backend/reading_check.py` — Plan A working
- `backend/audio.py`, `backend/db.py`, `backend/tips.py` — complete
- `backend/seed.py` — real stories, no placeholders
- `start_dinig.bat` — correct
- `requirements.txt` — no new packages needed

---

## After Phase 4: remaining phases

### Phase 5 — Offline verification and demo prep
1. `copy .env.example .env` on demo laptop
2. Run full demo flow 3× with Wi-Fi off:
   - `/health` → all 4 flags true
   - Pick Mika → story → read → colored result → quiz → practice → all done
   - Teacher view: Mika at top with AI tip
   - `temp/` folder empty after each run
3. Add Qwen warm-up at startup in `lifespan()` in `backend/main.py`:
   ```python
   if local_models.ollama_ready():
       local_models.generate("ping", timeout=30)  # warm up; response ignored
   ```
4. Measure and record actual speeds (Done→result, quiz question time, AI tip time)
5. Update README with real measurements

---

## How to run the app (dev mode, macOS)
```bash
cd /Users/macbookprom1/Documents/GitHub/dinig
venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
# Open http://localhost:8000 in browser
```

## How to reset demo data
```bash
venv/bin/python backend/seed.py
```

## How to run all tests
```bash
venv/bin/python tests/test_reading_check.py
venv/bin/python tests/test_phase1.py
node tests/test_phase3_frontend.js
```

---

## Key docs to read before working
- `docs/PRD.md` — what to build, what not to build, demo script
- `docs/BRAND.md` — colors, fonts, tone, do/don't
- `docs/SITEMAP.md` — every screen and how they connect
- `docs/API.md` — every API route
- `docs/COMPLETION_PLAN.md` — full phase-by-phase plan with status
- `AGENTS.md` — project rules (no cloud AI, no npm, plain HTML/CSS/JS)
