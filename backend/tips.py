"""Rule-based teacher tip. Saved right after every reading, so the Class View
always has a tip even when the local AI is slow or off."""


def rule_based_tip(practice_words: list[str]) -> str:
    unique = list(dict.fromkeys(w for w in practice_words if w))[:3]
    if not unique:
        return "Great reading! Try a new story."
    return "Practice: " + ", ".join(unique) + "."
