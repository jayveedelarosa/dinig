"""Small text helpers shared by the seed script and the reading check."""
import re

# Seed stories start with this marker until the team writes the real stories.
PLACEHOLDER_RE = re.compile(r"^\s*\[PLACEHOLDER[^\]]*\]\s*")


def clean_story(text: str) -> str:
    """Story text without the placeholder marker (what the pupil sees and reads)."""
    return PLACEHOLDER_RE.sub("", text)


def normalize(word: str) -> str:
    """Lowercase, no punctuation: "Lito's," -> "litos"."""
    return re.sub(r"[^\w]", "", word.lower()).replace("_", "")


def story_tokens(text: str) -> list[str]:
    """Story split into display words (punctuation kept). Hyphens split words,
    because Whisper often writes "mango-tree" as "mango tree"."""
    tokens = clean_story(text).replace("-", " ").replace("—", " ").split()
    return [t for t in tokens if normalize(t)]


def words(text: str) -> list[str]:
    """Normalized word list for comparing (lowercase, no punctuation)."""
    return [n for n in (normalize(t) for t in text.replace("-", " ").split()) if n]
