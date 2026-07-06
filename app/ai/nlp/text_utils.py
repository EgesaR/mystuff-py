"""Text post-processing for dictation / lyrics transcription.

Two modes
---------
  "speech"  — standard dictation: spell-correct, wordninja compound recovery,
              grammar fixes, accent substitution.
  "lyrics"  — musical transcription: melisma cleanup, lyric-specific vocab,
              structural line detection, no aggressive spell correction.
"""

import re
from typing import Literal

from app.ai.accent.learner import get_learner
from app.ai.accent.mappings import CUSTOM_MAPPINGS, CUSTOM_VOCAB, REAL_SHORT_WORDS
from app.ai.lyrics.processor import clean_lyric_line, process_lyrics

Mode = Literal["speech", "lyrics"]

# ── Optional: wordninja ─────────────────────────────────────────────────────
try:
    import wordninja as _wn  # type: ignore[import-untyped]
    WN_SPLIT = _wn.split
except ImportError:
    WN_SPLIT = None

# ── Optional: pyspellchecker ──────────────────────────────────────────────────
try:
    from spellchecker import SpellChecker
    SPELL: SpellChecker | None = SpellChecker(distance=1)
    SPELL.word_frequency.load_words(list(CUSTOM_VOCAB))
except ImportError:
    SPELL = None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _heal_bpe_fragments(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for tok in tokens:
        is_fragment = len(tok) <= 2 and tok.lower() not in REAL_SHORT_WORDS
        if is_fragment and out:
            out[-1] += tok
        else:
            out.append(tok)
    return out


def _split_suffix(word: str) -> tuple[str, str]:
    if word and word[-1] in ".,!?;:":
        return word[:-1], word[-1]
    return word, ""


def _is_acronym(word: str) -> bool:
    return 2 <= len(word) <= 6 and word.isupper()


# ── Speech pipeline ───────────────────────────────────────────────────────────

def _process_speech(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()

    for pattern, replacement in CUSTOM_MAPPINGS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r"(\w+)\s*'\s*(\w+)", r"\1'\2", text)

    tokens = text.split()
    tokens = _heal_bpe_fragments(tokens)
    text = " ".join(tokens)

    alpha_chars = [c for c in text if c.isalpha()]
    if alpha_chars and sum(c.isupper() for c in alpha_chars) / len(alpha_chars) > 0.6:
        text = text.lower()

    text = get_learner().apply(text)

    if WN_SPLIT is not None:
        recovered: list[str] = []
        for word in text.split():
            core, suffix = _split_suffix(word)
            if len(core) > 9 and core == core.lower() and core not in CUSTOM_VOCAB:
                parts = WN_SPLIT(core)
                if len(parts) > 1:
                    recovered.extend(parts[:-1])
                    recovered.append(parts[-1] + suffix)
                    continue
            recovered.append(word)
        text = " ".join(recovered)

    for pattern, replacement in CUSTOM_MAPPINGS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    if SPELL is not None:
        corrected: list[str] = []
        for word in text.split():
            core, suffix = _split_suffix(word)
            skip = (
                len(core) <= 3
                or "'" in core
                or _is_acronym(core)
                or (bool(core) and core[0].isupper())
                or core.lower() in CUSTOM_VOCAB
            )
            if skip:
                corrected.append(word)
                continue
            if core.lower() in SPELL:
                corrected.append(word)
            else:
                fix = SPELL.correction(core.lower())
                corrected.append((fix if fix else core.lower()) + suffix)
        text = " ".join(corrected)

    text = re.sub(r"\s+([.,!?;:])", r"\1", text)

    if text:
        text = text[0].upper() + text[1:]

    return text.strip()


# ── Lyrics pipeline ───────────────────────────────────────────────────────────

def _process_lyrics_interim(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    for pattern, replacement in CUSTOM_MAPPINGS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = get_learner().apply(text)
    text = clean_lyric_line(text)
    if text:
        text = text[0].upper() + text[1:]
    return text.strip()


def _process_lyrics_final(text: str, structured: bool = True) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    for pattern, replacement in CUSTOM_MAPPINGS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = get_learner().apply(text)
    return process_lyrics(text, structure=structured)


# ── Public API ──────────────────────────────────────────────────────────────

def fine_tune_text(text: str, mode: Mode = "speech") -> str:
    """Post-process a raw ASR interim transcript."""
    if mode == "lyrics":
        return _process_lyrics_interim(text)
    return _process_speech(text)


def fine_tune_final(text: str, mode: Mode = "speech", structured: bool = True) -> str:
    """Post-process a finalised utterance (endpoint detected)."""
    if mode == "lyrics":
        return _process_lyrics_final(text, structured=structured)
    return _process_speech(text)
