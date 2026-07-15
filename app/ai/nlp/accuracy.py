"""Word-level accuracy / WER scoring, shared by the speech and lyrics pipelines.

Two comparisons matter for this app:

  raw_vs_processed      — how much the post-processing pipeline changed the
                           raw ASR output. Useful as a cheap, reference-free
                           signal (no user ground truth needed).
  processed_vs_corrected — the text a user was shown vs. what they actually
                           corrected it to. This is the real accuracy metric.

Both produce an `AccuracyResult` so they can be logged identically.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import StrEnum

_WORD_RE = re.compile(r"\S+")


class AccuracyType(StrEnum):
    """Types of accuracy comparisons for the pipeline."""
    RAW_VS_PROCESSED = "raw_vs_processed"
    PROCESSED_VS_CORRECTED = "processed_vs_corrected"


@dataclass(frozen=True)
class AccuracyResult:
    """Data class representing the results of a WER calculation."""
    reference_words: int
    hypothesis_words: int
    matches: int
    substitutions: int
    deletions: int
    insertions: int
    word_error_rate: float
    word_accuracy: float

    def as_dict(self) -> dict[str, float | int]:
        """Convert the accuracy result into a dictionary structure."""
        return asdict(self)


def _tokenize(text: str, case_sensitive: bool) -> list[str]:
    words = _WORD_RE.findall(text or "")
    return words if case_sensitive else [w.lower() for w in words]


def word_accuracy(
    reference: str,
    hypothesis: str,
    case_sensitive: bool = False,
) -> AccuracyResult:
    """Compute WER-style accuracy of `hypothesis` against `reference`.

    Uses a single-pass, O(n*m) Levenshtein alignment at the word level with
    O(min(n, m)) memory (rolling two-row DP) rather than a full n*m matrix,
    which matters for long lyric transcripts / long dictation sessions.
    """
    ref = _tokenize(reference, case_sensitive)
    hyp = _tokenize(hypothesis, case_sensitive)
    n, m = len(ref), len(hyp)

    if n == 0:
        return AccuracyResult(
            reference_words=0,
            hypothesis_words=m,
            matches=0,
            substitutions=0,
            deletions=0,
            insertions=m,
            word_error_rate=1.0 if m else 0.0,
            word_accuracy=0.0 if m else 1.0,
        )

    # Rolling two-row DP for edit distance, keeping op counts alongside cost.
    # Each cell stores (cost, substitutions, deletions, insertions).
    prev_row: list[tuple[int, int, int, int]] = [
        (j, 0, 0, j) for j in range(m + 1)]

    for i in range(1, n + 1):
        curr_row: list[tuple[int, int, int, int]] = [(i, 0, i, 0)]
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                curr_row.append(prev_row[j - 1])
                continue

            sub_cost, sub_s, sub_d, sub_i = prev_row[j - 1]
            del_cost, del_s, del_d, del_i = prev_row[j]
            ins_cost, ins_s, ins_d, ins_i = curr_row[j - 1]

            best = min(sub_cost, del_cost, ins_cost)
            if best == sub_cost:
                curr_row.append((sub_cost + 1, sub_s + 1, sub_d, sub_i))
            elif best == del_cost:
                curr_row.append((del_cost + 1, del_s, del_d + 1, del_i))
            else:
                curr_row.append((ins_cost + 1, ins_s, ins_d, ins_i + 1))
        prev_row = curr_row

    cost, subs, dels, ins = prev_row[m]
    matches = n - subs - dels
    wer = cost / n
    accuracy = max(0.0, 1.0 - wer)

    return AccuracyResult(
        reference_words=n,
        hypothesis_words=m,
        matches=matches,
        substitutions=subs,
        deletions=dels,
        insertions=ins,
        word_error_rate=round(wer, 4),
        word_accuracy=round(accuracy, 4),
    )
