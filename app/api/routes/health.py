"""api/routes/health.py

Simple health-check endpoint — no auth required.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db

router = APIRouter()


@router.get(
    "",
    summary="Health check",
    tags=["Health"],
)
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Return the API health status.
    
    Args:
        db (Session): Database session.
    
    Returns:
        dict[str, str]: Response payload.
    """
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except SQLAlchemyError:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
    }
