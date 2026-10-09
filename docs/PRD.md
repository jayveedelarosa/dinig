# PRD: Dinig

## Problem (one sentence)
Grade 3 and 4 public school pupils struggle to read simple texts because no one has time to listen to each of them read aloud.

## Who has it (ideal customer: age, place, job, device, budget)
- **Buyer and main user:** a public school teacher, 30 to 50 years old, in a rural Philippine school with weak or no internet.
- **Class:** 40+ pupils in Grade 3 or 4 (about 8 to 10 years old).
- **Device:** one shared Windows laptop with **8GB RAM** (a typical DepEd laptop) and no graphics card. Pupils use it one at a time. No phone or internet needed. [CHANGED]
- **Budget:** earns about P30,000 to P35,000 a month. Pays nothing for Dinig (pricing is an OPEN QUESTION).
- **Secondary user: parents** at home, using a family Windows laptop for their own child: a "class" of one. They use the same screens as the teacher, through the **Teacher / Parent** button. There is no separate parent mode. [CHANGED]

## Why it matters (Real, Large, Significant, Relevant, Urgent, with sources)
- **Real:** 91% of Filipino 10-year-olds are in "learning poverty", meaning they cannot read and understand a simple text (World Bank, via Inquirer [1]).
- **Large:** OPEN QUESTION. Market size numbers are still being gathered by our pitcher.
- **Significant:** learning poverty rose from 69.5% in 2019 to 91% [2].
- **Relevant:** almost 12,000 public schools have no internet (SONA 2025, via The Post [3]), so cloud reading apps cannot reach them.
- **Urgent:** the number is going up, not down [2], and every year a child cannot read makes every other subject harder.

## Root cause (5 whys)
1. Why can't pupils read simple texts? They don't get enough practice reading aloud with someone who corrects them.
2. Why not? One teacher has 40+ pupils and cannot listen to each one read every day.
3. Why can't technology listen for the teacher? Most reading apps need the internet, and the school has weak or no internet.
4. Why not just get internet? Almost 12,000 public schools have none [3], and fixing that is outside a teacher's control.
5. Why not send recordings to the cloud later? These are recordings of children's voices, and they should not leave the school.

**Root cause:** no affordable, private, offline way to listen to every pupil read and tell the teacher who needs help.

## Solution (one sentence)
Dinig listens to each pupil read a short story aloud on the classroom laptop, highlights missed words, checks understanding, and gives the teacher a one-screen class view with a tip for each pupil, all with Wi-Fi off.
Dinig is a desktop app: double-click it and it opens in its own window, then runs fully offline with no internet, no phone and no account. [CHANGED]

## Why local (REQUIRED in our submission)
- **Privacy:** recordings of children's voices (minors) are turned into text and scored on the laptop, then deleted right away. Only scores, reading times and trouble words are saved. The same is true at home: a child reading to a parent's laptop never sends their voice anywhere. [CHANGED]
- **Offline:** almost 12,000 public schools have no internet [3], and many others have a weak signal. Dinig works the same with Wi-Fi off, any day, in any classroom. It needs no internet, no phone and no cloud account at any point after setup. Families without home internet can use it too. [CHANGED]
- **Speed:** a child who just read aloud needs feedback right away while the story is still fresh, and a slow or dropped cloud upload would break that moment. (Our actual speed is an OPEN QUESTION until we measure it.)
- **Cost:** cloud speech-to-text and AI calls cost money per use. A class of 40+ reading every week would cost the school something every month. Running locally costs nothing after setup. It runs on the 8GB laptops schools and families already have, with no new hardware. [CHANGED]
- **Impossible with cloud:** for a school with no internet, a cloud version simply does not work. Local is the only version that can exist there.

## Core features (in priority order, each with 1 to 3 "done when" checks)
1. **Read and Check (with Timer)**: the demo depends on this.
   - Done when, with Wi-Fi off, a pupil reads a story, taps Done, and every word turns green (correct), red (wrong) or grey (skipped).
   - Done when the screen shows "42 of 50 words correct" plus the reading time.
   - Done when the audio file is gone from the laptop after scoring.
2. **Teacher's Class View (with Heatmap)**
   - Done when one screen lists every pupil with latest score, reading time, trouble words and a one-line tip.
   - Done when the heatmap shows each pupil's last 5 readings as colored cells.
   - Done when the pupil from the live demo appears on it without restarting anything.
   - Done when a parent can add one child and use the same Class View for that child only (no separate parent mode). [CHANGED]
3. **Story Quiz** (Story Comprehension Auto-Quizzer)
   - Done when 2 questions about the story appear after the result. Pre-written questions appear if the AI takes more than 8 seconds.
   - Done when the child answers out loud and gets "right" or "not yet" with a short, encouraging message.
4. **Practice Again**: first to cut.
   - Done when the AI writes 2 to 3 short, easy sentences using the child's red words.
   - Done when, after reading them, the screen shows "Before: 3 wrong words. Now: 1 wrong word."
   - Done when words still missed show up in that pupil's trouble words in the Class View.

**Extras (only if all 4 core features work by 12:00 AM):** words per minute, and 2 short Filipino stories.

## The demo "wow moment" (with Wi-Fi turned off, step by step, under 2 minutes)
1. (0:00) Show the Windows taskbar: Wi-Fi is **off**, and no phone is connected. Double-click **Dinig** (start_dinig.bat): it opens in its own window. [CHANGED]
2. (0:10) Tap **I'm a Pupil**, then pick "Mika", then pick the story.
3. (0:20) A teammate reads the story aloud like a Grade 3 pupil, misreading 2 words and skipping 1 on purpose. Tap **Done**.
4. (0:45) Words light up green, red and grey. The screen shows "47 of 50 words correct" and the time.
5. (1:00) **Story Quiz:** answer one question out loud and get an encouraging reply.
6. (1:20) Tap **Teacher / Parent** to open the **Class View**. [CHANGED] Mika is at the top with their score, trouble words and a tip written by the local AI. The heatmap shows the whole class at a glance.
7. (1:45) Closing line: "No internet was used. The child's voice never left this laptop."

Backup plan if the demo goes wrong: pre-written questions and rule-based tips (see SYSTEM_DESIGN, Fallbacks). Never a recorded video.

## How we are different (vs existing reading apps)
Reading apps such as Google Read Along are built for one child practicing alone. Dinig is built for the **teacher** who manages 40+ pupils on **one shared laptop**:
- a Class View and heatmap showing who needs help, in one glance
- a plain tip from the local AI for every pupil
- the whole class shares one device with no accounts, and it works with no internet at all
- a desktop app that runs on an 8GB laptop with no internet and no phone [CHANGED]
- the same app works at home for a parent with one child [CHANGED]

## Out of scope (things we will NOT build this weekend)
Mention these only as "what's next":
- tap-a-word pronunciation playback (text-to-speech)
- a full adaptive learning path
- a large Filipino and local-language story library
- downloadable reading materials
- sharing data between laptops by QR code
- user accounts or passwords
- cloud sync
- a separate parent mode or parent accounts [CHANGED]
- a phone or mobile app [CHANGED]

## Success looks like (what must work by 4:00 AM)
- [ ] With Wi-Fi off, a full run works: Read Aloud, then My Result with colored words, score and time.
- [ ] Audio files are deleted after every scoring.
- [ ] Class View shows 10 seed pupils plus the demo pupil, with heatmap and tips.
- [ ] Story Quiz shows 2 questions and judges a spoken answer, with fallback questions working.
- [ ] Practice Again shows "Before / Now" (or it has been cut on purpose).
- [ ] `GET /health` reports both models loaded. The demo has been run start to finish 3 times on the demo laptop.
- [ ] Every model and tool is listed in the README.
- [ ] Double-clicking start_dinig.bat opens Dinig in an Edge app window with no tabs or address bar. [CHANGED]
- [ ] A full demo run works on an 8GB RAM laptop (with qwen2.5:1.5b if needed). [CHANGED]
- [ ] With Wi-Fi off, double-clicking start_dinig.bat opens Dinig and /health shows both models loaded. [CHANGED]

## Cut order (what to drop first if we run out of time)
1. Extras (words per minute, Filipino stories)
2. Practice Again (Core 4)
3. AI answer judging, replaced by keyword matching against the backup answer
4. AI-written quiz questions, replaced by pre-written questions only
5. AI-written tips, replaced by rule-based tips ("Practice: word1, word2")
6. Heatmap, replaced by the table only

Never cut: Read and Check, and the Class View table.

## Sources
1. World Bank, via Inquirer: https://newsinfo.inquirer.net/1632864/wb-ph-learning-poverty-among-highest-in-region
2. Inquirer: https://newsinfo.inquirer.net/?p=1651996
3. SONA 2025, via The Post: https://thepost.net.ph/?p=71502
