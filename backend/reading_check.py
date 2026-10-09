"""Reading check: the ONE module that decides green / red / grey for each story word.

The rest of the app only calls check_reading(). READING_CHECK in .env picks the plan:
- plan_a (default): Whisper writes down what was said, difflib lines it up with the story.
- plan_b: MMS forced alignment (torchaudio). Not built yet.
"""
from difflib import SequenceMatcher

from backend import config
from backend.ai import local_models
from backend.text_utils import normalize, story_tokens, words


def check_reading(wav_path, story_text: str, language: str = "en") -> list[dict]:
    """Returns [{"word": "Lito", "status": "green" | "red" | "grey"}, ...] for every story word."""
    if config.READING_CHECK == "plan_b":
        return _plan_b(wav_path, story_text)
    transcript = local_models.transcribe(wav_path, language)
    return score_words(story_text, transcript)


def score_words(story_text: str, transcript: str) -> list[dict]:
    """Plan A scoring (pure function, easy to test without audio).

    Both texts are lowercased with punctuation removed, then difflib's opcodes say:
      equal   -> story words read correctly  -> green
      replace -> child said something else   -> red
      delete  -> story words with no match   -> grey (skipped)
      insert  -> extra words (repeats, restarts) -> ignored, never red
    Story names (like "Lito") are green on a close spelling match, because
    Whisper often spells names a little differently ("Leto").
    """
    tokens = story_tokens(story_text)            # what we display, punctuation kept
    story = [normalize(t) for t in tokens]        # what we compare
    said = words(transcript)
    names = _story_names(tokens)

    status = ["grey"] * len(story)
    matcher = SequenceMatcher(a=story, b=said, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            status[i1:i2] = ["green"] * (i2 - i1)
        elif tag == "replace":
            for i in range(i1, i2):
                close = story[i] in names and any(_close_match(story[i], h) for h in said[j1:j2])
                status[i] = "green" if close else "red"
        # "delete" stays grey; "insert" touches no story word
    return [{"word": t, "status": s} for t, s in zip(tokens, status)]


def _story_names(tokens: list[str]) -> set[str]:
    """Capitalized words that are names: either capitalized in the middle of a sentence
    ("Nena"), or always capitalized and used at least twice ("Lito" at two sentence starts).
    One-time sentence starters like "Every" or "The" are not names."""
    capitalized_mid, capitalized_count, lowercase = set(), {}, set()
    sentence_start = True
    for tok in tokens:
        bare = tok.lstrip("\"'“‘")
        starts = sentence_start or bare != tok  # a quote also starts a sentence
        word = normalize(tok)
        if bare[:1].isupper():
            capitalized_count[word] = capitalized_count.get(word, 0) + 1
            if not starts:
                capitalized_mid.add(word)
        else:
            lowercase.add(word)
        sentence_start = tok.rstrip("\"'”’").endswith((".", "!", "?"))
    repeated = {w for w, n in capitalized_count.items() if n >= 2 and w not in lowercase}
    return capitalized_mid | repeated


def _close_match(name: str, heard: str) -> bool:
    """Small spelling difference only: same first letter and 70% similar ("lito" ~ "leto")."""
    return heard[:1] == name[:1] and SequenceMatcher(None, name, heard).ratio() >= 0.7


def summarize(result: list[dict]) -> dict:
    """Score plus the red / skipped word lists saved in the readings table."""
    red = [normalize(w["word"]) for w in result if w["status"] == "red"]
    skipped = [normalize(w["word"]) for w in result if w["status"] == "grey"]
    return {
        "words_correct": sum(1 for w in result if w["status"] == "green"),
        "total_words": len(result),
        "red_words": red,
        "skipped_words": skipped,
    }


def _plan_b(wav_path, story_text: str) -> list[dict]:
    # TODO [BACKEND]: Plan B, forced alignment with torchaudio.pipelines.MMS_FA.
    # Align each story word to the audio: low score -> red, no audio -> grey.
    # Test memory on the 8GB laptop with Whisper and Qwen also loaded (OPEN QUESTION).
    raise NotImplementedError("Plan B (MMS aligner) is not built yet. Set READING_CHECK=plan_a in .env.")
