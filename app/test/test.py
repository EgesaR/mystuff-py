from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print(PROJECT_ROOT)
from app.database.session import engine

inspector = inspect(engine)
print("USERS")
for column in inspector.get_columns("users"):
    print(
        f"  {column['name']} "
        f"{column['type']}"
    )
    print("PRE_REGISTRATIONS")
    for column in inspector.get_columns("pre_registrations"):
        print(
            f"  {column['name']} "
            f"{column['type']}"
        )
        print("PRE_REGISTRATION FKs")
        for fk in inspector.get_foreign_keys("pre_registrations"):
            print(fk)
