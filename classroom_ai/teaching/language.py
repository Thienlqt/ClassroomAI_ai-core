from __future__ import annotations

import re

from classroom_ai.schemas import SpeechSegment


_SEGMENT_PATTERN = re.compile(
    r"\[(en|vi)\](.*?)\[/\1\]",
    flags=re.IGNORECASE | re.DOTALL,
)
_ANY_LANGUAGE_TAG = re.compile(r"\[/?(?:en|vi)\]", flags=re.IGNORECASE)
_VIETNAMESE_CHARACTERS = re.compile(
    r"[ăâđêôơưĂÂĐÊÔƠƯàáạảãằắặẳẵầấậẩẫèéẹẻẽềếệểễ"
    r"ìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹ"
    r"ÀÁẠẢÃẰẮẶẲẴẦẤẬẨẪÈÉẸẺẼỀẾỆỂỄ"
    r"ÌÍỊỈĨÒÓỌỎÕỒỐỘỔỖỜỚỢỞỠÙÚỤỦŨỪỨỰỬỮỲÝỴỶỸ]"
)


def _language_for_untagged_text(text: str) -> str:
    return "vi-VN" if _VIETNAMESE_CHARACTERS.search(text) else "en-US"


def _append_segment(segments: list[SpeechSegment], language: str, text: str) -> None:
    clean_text = " ".join(_ANY_LANGUAGE_TAG.sub("", text).split())
    if not clean_text:
        return
    if segments and segments[-1].language == language:
        segments[-1].text = f"{segments[-1].text} {clean_text}"
    else:
        segments.append(SpeechSegment(language=language, text=clean_text))


def parse_speech_segments(content: str) -> list[SpeechSegment]:
    """Turn model language tags into safe, ordered TTS segments.

    Untagged model replies remain backward compatible and are treated as English,
    unless they contain unmistakable Vietnamese characters.
    """

    clean_content = content.strip()
    if not clean_content:
        return []

    segments: list[SpeechSegment] = []
    cursor = 0
    for match in _SEGMENT_PATTERN.finditer(clean_content):
        prefix = clean_content[cursor : match.start()]
        _append_segment(segments, _language_for_untagged_text(prefix), prefix)
        language = "vi-VN" if match.group(1).casefold() == "vi" else "en-US"
        _append_segment(segments, language, match.group(2))
        cursor = match.end()

    remainder = clean_content[cursor:]
    _append_segment(segments, _language_for_untagged_text(remainder), remainder)
    return segments
