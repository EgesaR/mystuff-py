"""Text post-processing for dictation / lyrics transcription.

Two modes
---------
  "speech"  — standard dictation: spell-correct, wordninja compound recovery,
              grammar fixes, accent substitution.
  "lyrics"  — musical transcription: melisma cleanup, lyric-specific vocab,
              structural line detection, no aggressive spell correction.

Accuracy
--------
`fine_tune_final_scored` / `fine_tune_text_scored` wrap the normal pipeline
and additionally return an `AccuracyResult` (see `app.ai.nlp.accuracy`) so
callers (websocket handlers, services) can log word accuracy without this
module knowing anything about the database. The plain `fine_tune_*`
functions are unchanged and remain the ones to use when you don't need
metrics.
"""

import re
from collections.abc import Callable
from typing import Any, Literal, cast

from app.ai.accent.learner import get_learner
from app.ai.accent.mappings import CUSTOM_MAPPINGS, CUSTOM_VOCAB, REAL_SHORT_WORDS
from app.ai.lyrics.processor import clean_lyric_line, process_lyrics
from app.ai.nlp.accuracy import AccuracyResult, AccuracyType, word_accuracy

Mode = Literal["speech", "lyrics"]

# ── Optional: wordninja ─────────────────────────────────────────────────────
try:
    import wordninja as _wn  # type: ignore[import-untyped]
    _wn_split: Any = cast(Any, _wn).split
except ImportError:
    _wn_split = None

WN_SPLIT: Callable[[str], list[str]] | None = _wn_split


# ── Optional: pyspellchecker ──────────────────────────────────────────────────
try:
    from spellchecker import SpellChecker
    _spell: Any = SpellChecker(distance=1)
    _spell.word_frequency.load_words(list(CUSTOM_VOCAB))
except ImportError:
    _spell = None

SPELL: Any = _spell


# ── Precompiled patterns ─────────────────────────────────────────────────────
# Compiling once at import time (instead of re.compile-under-the-hood on every
# re.sub call, twice per utterance) is the single biggest hot-path win here.
_CUSTOM_MAPPINGS_COMPILED: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in CUSTOM_MAPPINGS.items()
]
_WHITESPACE_RE = re.compile(r"\s+")
_APOSTROPHE_RE = re.compile(r"(\w+)\s*'\s*(\w+)")
_PUNCT_SPACE_RE = re.compile(r"\s+([.,!?;:])")


def _apply_custom_mappings(text: str) -> str:
    for pattern, replacement in _CUSTOM_MAPPINGS_COMPILED:
        text = pattern.sub(replacement, text)
    return text


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
    text = _WHITESPACE_RE.sub(" ", text).strip()

    text = _apply_custom_mappings(text)
    text = _APOSTROPHE_RE.sub(r"\1'\2", text)

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

    # Re-applied because wordninja/learner substitutions can surface new
    # contractions ("gonna"/"ta") that weren't present before splitting.
    text = _apply_custom_mappings(text)

    if SPELL is not None:
        corrected: list[str] = []
        # Batch the "already correct" check: SpellChecker.known() does a single
        # set intersection instead of an unsupported `word in SPELL` membership
        # test per word (SpellChecker has no __contains__, so the previous
        # `core.lower() in SPELL` was silently falling through to iterating the
        # object and comparing — effectively meaningless — before erroring or
        # always failing depending on version). known() is both correct and
        # faster since it's one call instead of N.
        words = text.split()
        candidates: list[str] = []
        cores: list[tuple[str, str, bool]] = []  # (core, suffix, skip)
        for word in words:
            core, suffix = _split_suffix(word)
            skip = (
                len(core) <= 3
                or "'" in core
                or _is_acronym(core)
                or (bool(core) and core[0].isupper())
                or core.lower() in CUSTOM_VOCAB
            )
            cores.append((core, suffix, skip))
            if not skip:
                candidates.append(core.lower())

        known_words: set[str] = SPELL.known(
            candidates) if candidates else set()

        for word, (core, suffix, skip) in zip(words, cores, strict=True):
            if skip or core.lower() in known_words:
                corrected.append(word)
                continue
            fix = SPELL.correction(core.lower())
            corrected.append((fix if fix else core.lower()) + suffix)
        text = " ".join(corrected)

    text = _PUNCT_SPACE_RE.sub(r"\1", text)

    if text:
        text = text[0].upper() + text[1:]

    return text.strip()


# ── Lyrics pipeline ───────────────────────────────────────────────────────────

def _process_lyrics_interim(text: str) -> str:
    if not text:
        return ""
    text = _WHITESPACE_RE.sub(" ", text).strip()
    text = _apply_custom_mappings(text)
    text = get_learner().apply(text)
    text = clean_lyric_line(text)
    if text:
        text = text[0].upper() + text[1:]
    return text.strip()


def _process_lyrics_final(text: str, structured: bool = True) -> str:
    if not text:
        return ""
    text = _WHITESPACE_RE.sub(" ", text).strip()
    text = _apply_custom_mappings(text)
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


def fine_tune_final_scored(
    text: str,
    mode: Mode = "speech",
    structured: bool = True,
) -> tuple[str, AccuracyResult]:
    """Same as `fine_tune_final`, plus a raw-vs-processed accuracy score.

    This is reference-free: it measures how much the pipeline had to change
    relative to the raw ASR text, which is a useful proxy signal even before
    any human correction exists. Callers that have a DB session should log
    the returned `AccuracyResult` via `LogService.log_accuracy(...)` with
    `AccuracyType.RAW_VS_PROCESSED`.
    """
    processed = fine_tune_final(text, mode=mode, structured=structured)
    metrics = word_accuracy(reference=text, hypothesis=processed)
    return processed, metrics


def fine_tune_text_scored(
    text: str,
    mode: Mode = "speech",
) -> tuple[str, AccuracyResult]:
    """Interim-transcript counterpart of `fine_tune_final_scored`."""
    processed = fine_tune_text(text, mode=mode)
    metrics = word_accuracy(reference=text, hypothesis=processed)
    return processed, metrics


__all__ = [
    "Mode",
    "fine_tune_text",
    "fine_tune_final",
    "fine_tune_final_scored",
    "fine_tune_text_scored",
    "AccuracyResult",
    "AccuracyType",
]
