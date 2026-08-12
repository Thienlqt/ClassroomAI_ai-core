import re


_VISUAL_REFERENCE_PATTERNS = (
    r"\blook at\b",
    r"\bpicture\b",
    r"\bimage\b",
    r"\bon (?:the|your) screen\b",
    r"\b(?:show|display)(?:ing|ed)? (?:you )?(?:a|an|the)\b",
)


def refers_to_unavailable_visual(text: str) -> bool:
    """Detect claims that require a successfully rendered visual action."""
    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in _VISUAL_REFERENCE_PATTERNS
    )
