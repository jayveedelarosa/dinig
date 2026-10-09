"""Reset the database and load the SAMPLE class for the demo.

Run from the project folder:
    venv\\Scripts\\python.exe backend\\seed.py

All pupils and results here are made-up sample data (the app labels them
"Sample class").
"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so "backend" imports work

from backend import db  # noqa: E402
from backend.config import DB_PATH  # noqa: E402
from backend.text_utils import normalize, story_tokens  # noqa: E402
from backend.tips import rule_based_tip  # noqa: E402

STORIES = [
    {
        # ~52 words. Harder words: bridge, careful, narrow, current.
        "title": "The Boat on the River",
        "text": (
            "Lito has a small boat. Every morning he rows across the river to school. "
            "The water is calm and clear. One day it rained hard and the current was strong. "
            "The bridge was narrow and slippery. Lito was careful. "
            "He tied his boat to a post and waited with his friend Nena "
            "until the rain stopped and the river was calm again."
        ),
        "questions": [
            ("Why did Lito tie his boat to a post?",
             "Because it rained and the current was strong."),
            ("What was narrow and slippery?",
             "The bridge."),
        ],
    },
    {
        # ~54 words. Harder words: branch, shade, climbed, careful, shared.
        "title": "The Mango Tree",
        "text": (
            "Behind the school there is a big mango tree. "
            "The children like to sit in its shade after lunch. "
            "In summer the mangoes turn yellow and sweet. "
            "Ana climbed the tree to pick one, but the branch bent under her feet. "
            "Her teacher called, \"Please come down carefully.\" "
            "Ana came down and shared the mango with her friends."
        ),
        "questions": [
            ("Why did the teacher ask Ana to come down?",
             "Because the branch bent under her feet."),
            ("What did Ana do with the mango?",
             "She shared it with her friends."),
        ],
    },
    {
        # ~53 words. Harder words: carabao, harvest, thunder, shelter.
        "title": "Rain on the Farm",
        "text": (
            "Tatay works on the farm with his carabao. "
            "The carabao helps pull the plow before the harvest. "
            "One afternoon dark clouds filled the sky. "
            "Thunder rumbled and the rain came down fast. "
            "Ben ran to help his father lead the carabao to shelter. "
            "They sat inside and drank warm salabat while they waited for the sun."
        ),
        "questions": [
            ("What does the carabao help Tatay do on the farm?",
             "It helps pull the plow."),
            ("Where did Ben and his father bring the carabao when it rained?",
             "To the shelter."),
        ],
    },
]

# (first name, grade, level). Levels: good ~90%+, almost ~75-89%, help <75%.
PUPILS = [
    ("Bea", 3, "good"), ("Carlo", 3, "almost"), ("Dindo", 4, "help"), ("Ella", 3, "good"),
    ("Franco", 4, "almost"), ("Gabby", 3, "help"), ("Hannah", 4, "good"), ("Isko", 3, "almost"),
    ("Jun", 4, "help"), ("Kyla", 3, "almost"),
]
DEMO_PUPIL = ("Mika", 3)  # no readings yet: the live demo result is clearly new

LEVELS = {  # accuracy range, words-per-minute range (made-up sample values)
    "good": ((0.90, 0.98), (70, 90)),
    "almost": ((0.76, 0.89), (50, 70)),
    "help": ((0.55, 0.74), (30, 50)),
}


def seed() -> None:
    rng = random.Random(2026)  # same sample class every time
    if DB_PATH.exists():
        DB_PATH.unlink()
    db.init_db()
    now = datetime.now().replace(microsecond=0)

    with db.connect() as conn:
        story_rows = []
        for s in STORIES:
            cur = conn.execute(
                "INSERT INTO stories (title, language, full_text, grade_level) VALUES (?, 'en', ?, 3)",
                (s["title"], s["text"]),
            )
            sid = cur.lastrowid
            for q, a in s["questions"]:
                conn.execute("INSERT INTO questions (story_id, question, answer) VALUES (?, ?, ?)", (sid, q, a))
            words = [normalize(t) for t in story_tokens(s["text"])]
            hard = sorted({w for w in words if len(w) >= 5})
            story_rows.append((sid, words, hard))

        all_hard = sorted({w for _, _, hard in story_rows for w in hard})

        for name, grade, level in PUPILS:
            (acc_lo, acc_hi), (wpm_lo, wpm_hi) = LEVELS[level]
            pet_words = rng.sample(all_hard, 3)  # this pupil's usual trouble words
            cur = conn.execute("INSERT INTO pupils (first_name, grade) VALUES (?, ?)", (name, grade))
            pid = cur.lastrowid

            count = rng.randint(3, 5)
            days_ago = sorted(rng.sample(range(1, 15), count), reverse=True)
            last_red = []
            for d in days_ago:
                sid, words, hard = rng.choice(story_rows)
                total = len(words)
                wrong = max(1, round(total * (1 - rng.uniform(acc_lo, acc_hi))))
                pool = [w for w in pet_words if w in words] + rng.sample(hard, len(hard))
                picked = list(dict.fromkeys(pool))[:wrong]
                picked += rng.sample([w for w in words if w not in picked], wrong - len(picked))
                n_skip = wrong // 4
                skipped, red = picked[:n_skip], picked[n_skip:]
                seconds = round(total / rng.uniform(wpm_lo, wpm_hi) * 60)
                read_at = (now - timedelta(days=d, hours=rng.randint(0, 5))).isoformat(sep=" ")
                conn.execute(
                    "INSERT INTO readings (pupil_id, story_id, read_at, seconds_taken, words_correct, "
                    "total_words, red_words, skipped_words) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (pid, sid, read_at, seconds, total - wrong, total, db.to_json(red), db.to_json(skipped)),
                )
                last_red = red
            conn.execute("UPDATE pupils SET latest_tip = ? WHERE id = ?", (rule_based_tip(last_red), pid))

        conn.execute("INSERT INTO pupils (first_name, grade) VALUES (?, ?)", DEMO_PUPIL)

    print(f"Seeded {DB_PATH}: {len(STORIES)} stories, {len(PUPILS)} sample pupils + demo pupil Mika.")


if __name__ == "__main__":
    seed()
