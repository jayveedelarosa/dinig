# Brand

## Target user behavior (most important)
**Teacher (buyer and main user)**
- **Where they are, internet access, device:** in a rural public school with weak or no internet, using one shared Windows laptop for 40+ pupils.
- **How comfortable with apps:** OPEN QUESTION, to be confirmed by a teacher interview. We assume they are comfortable with everyday apps but have little time to learn new tools. If setup takes more than a minute, they will not use it.
- **What makes them trust an app:**
  - it works with Wi-Fi off
  - no accounts or passwords
  - children's voices are not stored
  - plain words, not charts full of jargon
- **What makes them leave:**
  - it needs internet
  - it is slow or crashes in front of the class
  - it makes extra paperwork
  - it shames a child
- **Buying power:** about P30,000 to P35,000 a month, and the laptop belongs to the school. Dinig must be free to the teacher. Who pays is an OPEN QUESTION.

**Pupil (daily user)**
- 8 to 10 years old, Grade 3 or 4, reading below grade level in many cases.
- Uses the laptop only on their turn. They may be shy about reading aloud, and some are not used to a touchpad. They need big targets and few words.
- They stay when they feel proud and leave when they feel judged.

## Tone of voice (one example sentence for the pupil, one for the teacher)
- **Pupil (warm, short, cheering):** "Great reading, Mika! Let's practice 3 words together."
- **Teacher (plain, fast, factual):** "Mika: 47 of 50 correct, 1 min 35 s. Practice: bridge, careful."
- In Pupil mode, never use "wrong", "fail" or "bad". Red words are called **practice words**.

## Colors (with hex codes, including the green, red, and grey for word results, readable for color-blind users)
**Word results.** Color is never the only signal, so each result also has a shape:
| Result | Text | Background | Extra cue (for color-blind users) | Pupil sees |
| --- | --- | --- | --- | --- |
| Green (correct) | `#0B5D45` | `#D1F0E4` | ✓ in legend | correct |
| Red (wrong) | `#9A3A00` | `#FDE0CC` | wavy underline | practice word |
| Grey (skipped) | `#4B5563` | `#E5E7EB` | dashed outline | skipped |

The green and red are based on the Okabe-Ito color-blind-safe palette (bluish green and vermillion), so they also differ in brightness.

**App colors**
| Use | Hex |
| --- | --- |
| Primary (buttons, header) | `#1E4E8C` (deep blue, white text on it) |
| Accent (stars, highlights) | `#F2B705` (sun yellow, dark text only) |
| Pupil background | `#FFF8EC` (warm cream) |
| Teacher background | `#F7F8FA` (light grey) |
| Main text | `#1F2933` |

**Heatmap cells:** the accuracy number is always printed inside each cell, so the heatmap does not rely on color alone. Grey is **not** used here, because grey means "skipped" on the result screen.
| Accuracy | Text | Background | Meaning |
| --- | --- | --- | --- |
| 90%+ | `#0B5D45` | `#D1F0E4` | on track (green) |
| 75 to 89% | `#7A5200` | `#FCEFC7` | almost there (amber) |
| below 75% | `#9A3A00` | `#FDE0CC` | needs help (red) |
| no reading yet | `#4B5563` | `#FFFFFF` | empty cell with a dash |

These cutoffs are a design choice, not research. OPEN QUESTION: confirm them with a teacher.

Check every text and background pair with a contrast checker and aim for at least 4.5:1.

## Fonts (large and easy for young readers)
- **Pupil mode: Andika** (SIL, free OFL license). It was designed for beginning readers and has simple "a" and "g" shapes.
  - Story text: 32 to 40px, line height 1.8
  - Buttons: at least 72px tall
- **Teacher mode: Atkinson Hyperlegible** (free OFL license). It is clear at small sizes, so 40 rows fit on one screen.
  - Base size: 16px
- Download both fonts once and **bundle them in `frontend/fonts/`**. Never link to Google Fonts, because the app must load offline.

## Do and don't
**Do**
- Use one big action per pupil screen.
- Cheer effort: "Good try!" and "You fixed 2 words!"
- Show the pupil's first name.
- Show a friendly loading animation for any wait.
- Keep the Teacher mode table dense and sortable, so all 40 pupils fit on one screen.
- Say "Works offline" and "Voice deleted after checking" on screen.

**Don't**
- Don't show red X marks, sad faces or rankings in Pupil mode.
- Don't make pupils type.
- Don't use long sentences or small text in Pupil mode.
- Don't rely on color alone.
- Don't invent stats or speed numbers anywhere in the app or pitch.
- Don't load anything from the internet (fonts, icons, scripts).
