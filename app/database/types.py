"""Custom SQLAlchemy database types."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import CHAR
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator[UUID]):
    """Platform-independent UUID type.

    PostgreSQL:
        Uses the native UUID type.

    SQLite:
        Stores canonical 36-character UUID strings.

    Python:
        Always exposes ``uuid.UUID`` objects.
    """

    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        """Select the appropriate database implementation."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(
                PostgreSQLUUID(as_uuid=True),
            )

        return dialect.type_descriptor(
            CHAR(36),
        )

    def process_bind_param(
        self,
        value: UUID | str | None,
        dialect: Dialect,
    ) -> UUID | str | None:
        """Convert Python UUID values for the database."""
        if value is None:
            return None

        if not isinstance(value, UUID):
            value = UUID(str(value))

        if dialect.name == "postgresql":
            return value

        return str(value)

    def process_result_value(
        self,
        value: UUID | str | None,
        dialect: Dialect,
    ) -> UUID | None:
        """Convert database values back into Python UUID objects."""
        if value is None:
            return None

        if isinstance(value, UUID):
            return value

        return UUID(str(value))
