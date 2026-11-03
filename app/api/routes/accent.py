"""Accent correction profile endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.transcription_service import TranscriptionService

router = APIRouter()


class AccentCorrectionRequest(BaseModel):
    """Validated transcript correction submitted by a client."""

    model_config = ConfigDict(extra="forbid")

    raw: str = Field(min_length=1, max_length=2_000)
    corrected: str = Field(min_length=1, max_length=2_000)

    @field_validator("raw", "corrected")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        """Reject whitespace-only corrections without modifying the text."""
        if not value.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return value


@router.post(
    "/corrections",
    summary="Submit an accent correction",
)
def submit_correction(
    payload: AccentCorrectionRequest,
) -> dict[str, object]:
    """Store a raw-to-corrected transcription example."""
    return TranscriptionService.submit_correction(
        payload.raw,
        payload.corrected,
    )


@router.get(
    "/profile",
    summary="Get the accent correction profile",
)
def get_profile() -> dict[str, object]:
    """Retrieve the current accent correction profile."""
    return TranscriptionService.get_profile()


@router.delete(
    "/corrections/{word}",
    summary="Forget an accent correction",
)
def forget_correction(word: str) -> dict[str, object]:
    """Remove a previously stored accent correction."""
    return TranscriptionService.forget_correction(word)
