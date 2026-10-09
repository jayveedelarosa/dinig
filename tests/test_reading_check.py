"""Tests for the Plan A reading check scoring (no audio or model needed).

Run from the project folder:
    venv\\Scripts\\python.exe tests\\test_reading_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.reading_check import score_words, summarize  # noqa: E402

STORY = ("Lito has a small boat. Every morning he rows across the river to school. "
         "The water is calm. Lito was careful. He walked home with his friend Nena.")


def statuses(transcript):
    """Status of the FIRST time each story word appears."""
    result = {}
    for w in score_words(STORY, transcript):
        result.setdefault(w["word"].strip(".,"), w["status"])
    return result


def check(name, transcript, expect):
    got = statuses(transcript)
    for word, status in expect.items():
        assert got[word] == status, f"{name}: {word!r} should be {status}, got {got[word]}"
    print(f"ok  {name}")


PERFECT = ("lito has a small boat every morning he rows across the river to school "
           "the water is calm lito was careful he walked home with his friend nena")

check("perfect reading", PERFECT, {"Lito": "green", "careful": "green", "Nena": "green"})
check("swapped word is red", PERFECT.replace("boat", "goat"), {"boat": "red", "small": "green"})
check("skipped word is grey", PERFECT.replace("careful ", ""), {"careful": "grey", "was": "green"})
check("repeats and restarts are ignored", PERFECT.replace("small", "small small").replace("every", "every every"),
      {"small": "green", "Every": "green"})

s = summarize(score_words(STORY, "Lito has a small boat"))
assert s["words_correct"] == 5 and s["red_words"] == [] and len(s["skipped_words"]) == s["total_words"] - 5
print("ok  stopped halfway: rest is grey")
s = summarize(score_words(STORY, ""))
assert s["words_correct"] == 0 and len(s["skipped_words"]) == s["total_words"]
print("ok  empty transcript: all grey")

# Story names: a close spelling match counts as correct
check("names with small spelling difference are green",
      PERFECT.replace("lito", "leto").replace("nena", "nina"), {"Lito": "green", "Nena": "green"})
check("a different name is still red", PERFECT.replace("lito has", "peter has"), {"Lito": "red"})
check("sentence-start word is not a name", PERFECT.replace("every", "ever"), {"Every": "red"})
check("'the' read as 'they' is still red", PERFECT.replace("the water", "they water"), {"The": "red"})

print("All reading check tests passed.")
