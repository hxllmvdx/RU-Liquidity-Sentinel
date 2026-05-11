from __future__ import annotations


class DatabaseError(RuntimeError):
    """Base database layer error."""


class DatabaseConnectionError(DatabaseError):
    """Raised when the service cannot connect to PostgreSQL."""


class DatabaseQueryError(DatabaseError):
    """Raised when a SQL query fails."""


class DatabaseTransactionError(DatabaseError):
    """Raised when a transaction cannot be committed or rolled back."""


class RecordNotFoundError(DatabaseError):
    """Raised when an expected row is missing."""


class FeatureUnavailableError(DatabaseError):
    """Raised when an optional DB capability such as pgvector is unavailable."""
