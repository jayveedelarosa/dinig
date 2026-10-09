# Future additions

Plans we are not building yet. Add the next idea as a new section. Build one only after the team agrees, because these sit outside the four core features in `PRD.md`.

## Teacher adds her own reading material

A teacher types one short passage on Class View. It is saved on the laptop and shows up on Pick a Story like the three sample stories. Pupils still do not type.

The product notes rule out a downloadable story library. This plan is one typed passage, stored in the existing `stories` table, with no file upload and no internet.

### What the teacher does

On Class View, next to Add Pupil, a form has three fields: title, grade (3 or 4), and the passage. **Add story** saves it. The next pupil who opens Pick a Story sees the new card and can read it. Read and Check, the quiz, and Practice Again use that text the same way they use a sample story.

The passage should stay short, about 20 to 80 words, so it fits the reading screen and Whisper stays quick. The form shows the word count and refuses an empty title or a passage outside that range.

Quiz questions are optional. If the teacher leaves them blank, Qwen writes two questions from the passage. If Qwen is slow or off and there are no saved questions, the quiz step is skipped and the pupil goes on to Practice Again or All Done. That skip already exists when a story has no questions.

### What stays the same

- No new database table. `POST /stories` inserts a row in `stories` (title, English, text, grade).
- Sample stories stay. Running `seed.py` still wipes the database, including any story the teacher added.
- No editing, deleting, file upload, or Filipino text in this slice.

### Files

- `backend/main.py` — `POST /stories` with the word limit.
- `frontend/index.html`, `frontend/app.js`, `frontend/styles.css` — the Class View form, matching Add Pupil.
- `docs/API.md`, `docs/SITEMAP.md`, and `docs/SYSTEM_DESIGN.md` — the new route and the Class View step.

### Check

Add a passage on Class View, open I'm a Pupil, and confirm the new card is there. Read it aloud and confirm the words score. With Qwen running, confirm two quiz questions appear. Turn Qwen off and confirm the quiz is skipped when no backup questions were saved.

## Windows setup wizard

**Status:** the wizard script is in the repo. `DinigSetup.exe` is built on a Windows laptop (this Mac cannot compile it). On that laptop, install Inno Setup 6 and double-click `packaging\build_setup.bat`. The file lands in `packaging\output\DinigSetup.exe`.

The teacher gets one file, **DinigSetup.exe**, and a normal Windows wizard: Next, Install, Finish. A Desktop icon named **Dinig** is left behind. Every later visit, she double-clicks that icon. She does not run the installer again.

The wizard is built with Inno Setup. The team builds it once on a laptop that has internet. Whisper, Qwen 3B, Qwen 1.5B, the app, and a seeded database are already inside the file, so the school laptop does not need Wi-Fi during install. The file is about 4GB, so it travels on a USB. The teacher laptop needs about 6GB free, because the Ollama program is installed beside the Dinig folder.

### What the teacher sees

1. **Welcome.** Dinig stays on this laptop, works with Wi-Fi off, and needs about 6GB free. No account.
2. **Folder.** It defaults to a folder in the teacher's own account, so it does not ask for an administrator password. If the disk is too full, the wizard stops and says so.
3. **Model.** Qwen 2.5 3B is selected. A second choice, 1.5B, is there for an 8GB laptop that is already crowded.
4. **Install.** A progress bar copies the app and Whisper, then installs Ollama in the background with `OllamaSetup.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES`. That install is per user and does not need an administrator. Qwen is placed in the Dinig folder, and the shortcut points `OLLAMA_MODELS` there.
5. **Finish.** A checked box says **Start Dinig**. One line says: when Edge asks for the microphone, click **Allow**.

Windows also gets an uninstall entry under Apps. A later update must not run `seed.py`, so pupils and stories already on the laptop stay.

### Every time she opens Dinig

The Desktop icon starts the local server, starts Ollama if it is not already running, and opens Dinig in its own window at `http://localhost:8000`. That address keeps the microphone allowed. App mode hides the address bar, and the window title is **Dinig**.

The icon looks for **Edge** first, then **Chrome**. Both can open that window with no tabs. If a laptop has neither, the icon opens the usual browser. An offline Edge installer is not in the wizard: that installer asks for an administrator, and this setup does not.

### What the wizard cannot click for them

Edge still asks for the microphone the first time. Windows may also show "Windows protected your PC" because the file is not from a paid code-signing certificate. The teacher chooses **More info**, then **Run anyway**.

### Check

On a Windows laptop that has never had Dinig, run the wizard with Wi-Fi off. Finish with the Desktop icon. Home says the local AI is ready. Close the window, double-click the icon again, and Dinig opens without the installer. Repeat once on a laptop with no Edge and confirm Chrome, or the default browser, opens the same page.
