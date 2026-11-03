from uuid import uuid4

from sqlalchemy import text

from app.database.session import engine

user_id = "c6f6b935-4df5-4f61-9184-6ee911f9b503"

with engine.begin() as conn:
    conn.execute(
        text("""
             INSERT INTO user_onboarding (
                user_id,
                version,
                completed,
                skipped,
                current_step,
                completed_at,
                id
            )
            VALUES (
                :user_id,
                :version,
                :completed,
                :skipped,
                :current_step,
                :completed_at,
                :id
            )
        """),
        {
            "user_id": user_id,
            "version": 1,
            "completed": False,
            "skipped": False,
            "current_step": 0,
            "completed_at": None,
            "id": str(uuid4()),
        },
    )
    print("Created onboarding state.")
