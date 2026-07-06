"""Adaptive accent correction engine.

Two layers:
  1. Pre-built phonetic substitution tables for common accent families.
  2. A learnable personal profile: corrections submitted by the user are
     extracted as token-level substitution patterns, persisted to JSON,
     and applied automatically once they reach the confidence threshold.
"""

import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal

from app.ai.accent.mappings import ACCENT_TABLES

AccentFamily = Literal["east_african", "indian",
                       "west_african", "british", "american", "auto"]


def _extract_substitutions(raw: str, corrected: str) -> list[tuple[str, str]]:
    """Diff two strings at word level; return (raw_word, correct_word) pairs."""
    raw_words = raw.lower().split()
    cor_words = corrected.lower().split()
    matcher = SequenceMatcher(None, raw_words, cor_words)
    pairs: list[tuple[str, str]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            raw_chunk = raw_words[i1:i2]
            cor_chunk = cor_words[j1:j2]
            if len(raw_chunk) == len(cor_chunk):
                for r, c in zip(raw_chunk, cor_chunk, strict=True):
                    if r != c and r.isalpha() and c.isalpha():
                        pairs.append((r, c))
            elif raw_chunk and cor_chunk:
                pairs.append((" ".join(raw_chunk), " ".join(cor_chunk)))

    return pairs


class AccentLearner:
    """Adaptive accent correction engine.

    Parameters
    ----------
    profile_path : Path
        JSON file storing learned corrections.
    accent_family : AccentFamily
        Pre-built table to load. "auto" loads east_african + american.
    min_confidence : int
        Minimum submissions before a correction fires automatically.
    """

    def __init__(
        self,
        profile_path: Path = Path("app/ai/accent/profiles/default.json"),
        accent_family: AccentFamily = "auto",
        min_confidence: int = 2,
    ) -> None:
        self.profile_path = profile_path
        self.min_confidence = min_confidence

        families = ["east_african", "american"] if accent_family == "auto" else [
            accent_family]
        self._builtin: list[tuple[str, str]] = []
        for fam in families:
            self._builtin.extend(ACCENT_TABLES.get(fam, []))

        self._learned: dict[str, dict[str, int]
                            ] = defaultdict(lambda: defaultdict(int))
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self.profile_path.exists():
            try:
                data = json.loads(
                    self.profile_path.read_text(encoding="utf-8"))
                for raw, corrections in data.items():
                    for cor, count in corrections.items():
                        self._learned[raw][cor] = count
            except (json.JSONDecodeError, KeyError):
                pass

    def save(self) -> None:
        """Persist learned corrections to disk."""
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        serialisable = {raw: dict(corrections)
                        for raw, corrections in self._learned.items()}
        self.profile_path.write_text(
            json.dumps(serialisable, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Learning ─────────────────────────────────────────────────────────────

    def learn(self, raw_text: str, corrected_text: str) -> int:
        """Register a correction. Returns number of pairs extracted."""
        pairs = _extract_substitutions(raw_text, corrected_text)
        for raw_token, cor_token in pairs:
            self._learned[raw_token][cor_token] += 1
        if pairs:
            self.save()
        return len(pairs)

    def forget(self, raw_token: str) -> None:
        """Remove all learned corrections for a token."""
        self._learned.pop(raw_token.lower(), None)
        self.save()

    @property
    def learned_rules(self) -> dict[str, str]:
        """High-confidence corrections only (count ≥ min_confidence)."""
        rules: dict[str, str] = {}
        for raw, corrections in self._learned.items():
            best = max(corrections, key=lambda c,
                       corrections=corrections: corrections[c])
            if corrections[best] >= self.min_confidence:
                rules[raw] = best
        return rules

    # ── Application ───────────────────────────────────────────────────────────

    def apply(self, text: str) -> str:
        """Apply pre-built + learned corrections to a transcript."""
        if not text:
            return text

        for pattern, replacement in self._builtin:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        rules = self.learned_rules
        if rules:
            words = text.split()
            corrected: list[str] = []
            for word in words:
                suffix = ""
                core = word
                if word and word[-1] in ".,!?;:":
                    suffix = word[-1]
                    core = word[:-1]
                lower_core = core.lower()
                if lower_core in rules:
                    fix = rules[lower_core]
                    if core and core[0].isupper():
                        fix = fix[0].upper() + fix[1:]
                    corrected.append(fix + suffix)
                else:
                    corrected.append(word)
            text = " ".join(corrected)

        rules_phrase = {k: v for k, v in rules.items() if " " in k}
        for raw_phrase, cor_phrase in rules_phrase.items():
            text = re.sub(
                r"\b" + re.escape(raw_phrase) + r"\b",
                cor_phrase,
                text,
                flags=re.IGNORECASE,
            )

        return text

    # ── Introspection ─────────────────────────────────────────────────────────

    def summary(self) -> str:
        rules = self.learned_rules
        lines = [
            f"Accent profile: {self.profile_path}",
            f"Pre-built rules: {len(self._builtin)}",
            f"Learned rules (≥{self.min_confidence} confirmations): {len(rules)}",
        ]
        if rules:
            lines.append("Top learned corrections:")
            for raw, cor in list(rules.items())[:10]:
                count = self._learned[raw][cor]
                lines.append(f"  '{raw}' → '{cor}'  ({count}×)")
        return "\n".join(lines)

    def export_learned(self) -> list[dict[str, str | int | bool]]:
        """Export all learned corrections as a list of dicts."""
        return [
            {
                "raw": raw,
                "correction": cor,
                "count": self._learned[raw][cor],
                "active": self._learned[raw][cor] >= self.min_confidence,
            }
            for raw, corrections in self._learned.items()
            for cor in corrections
        ]


# ── Module singleton ──────────────────────────────────────────────────────────
# pylint: disable=invalid-name
_default_learner: AccentLearner | None = None


def get_learner(
    profile_path: Path = Path("app/ai/accent/profiles/default.json"),
    accent_family: AccentFamily = "auto",
) -> AccentLearner:
    """Return (or lazily create) the module-level AccentLearner singleton."""
    global _default_learner  # pylint: disable=global-statement
    if _default_learner is None:
        _default_learner = AccentLearner(
            profile_path=profile_path,
            accent_family=accent_family,
        )
    return _default_learner
