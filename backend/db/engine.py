"""
Database engine factory.

Goal: let the existing `DatabaseManager` code (written for sqlite3
with `?` placeholders) run against either SQLite or PostgreSQL
without rewriting every query.

Strategy:
  * Parse DATABASE_URL.
  * For sqlite:///, return the native `sqlite3` connection the code
    already expects.
  * For postgresql://, return a shim connection that translates
    `?` placeholders to `%s`, and exposes `.execute`, `.cursor`,
    `.commit`, `.rollback`, `.close`, row-dict access — the same
    surface the code uses today.

This is a *bridge*, not the long-term home. When services are
extracted (P2) they should use SQLAlchemy ORM / Core directly via
`backend/models_sa.py`.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from typing import Any, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

_pg_available = False
try:
    import psycopg2  # noqa: F401
    import psycopg2.extras  # noqa: F401
    _pg_available = True
except ImportError:
    pass


def is_postgres_url(url: str) -> bool:
    return url.startswith("postgresql://") or url.startswith("postgres://")


def is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite:///") or url.startswith("sqlite://")


def sqlite_path(url: str) -> str:
    """Extract filesystem path from a sqlite URL."""
    return url.replace("sqlite:///", "").replace("sqlite://", "") or ":memory:"


# ------------------------------------------------------------------ #
# Postgres shim: makes a psycopg2 connection look like sqlite3
# ------------------------------------------------------------------ #
class _PgRow(dict):
    """Supports both row['col'] and row[0]."""

    def __init__(self, cursor, values):
        super().__init__()
        self._cols = [desc[0] for desc in cursor.description] if cursor.description else []
        for col, val in zip(self._cols, values):
            self[col] = val
        self._values = tuple(values)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class _PgCursor:
    def __init__(self, pg_cursor):
        self._c = pg_cursor
        self.lastrowid: Optional[int] = None

    @staticmethod
    def _translate(sql: str) -> str:
        # sqlite uses `?` placeholders; psycopg uses `%s`.
        # Percent-signs in LIKE patterns are passed as parameters,
        # so a naive replace here is safe.
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: Sequence[Any] = ()):
        try:
            self._c.execute(self._translate(sql), params)
            # Approximate SQLite's lastrowid semantics for INSERTs
            if self._c.description is None and sql.strip().upper().startswith("INSERT"):
                try:
                    self._c.execute("SELECT LASTVAL()")
                    row = self._c.fetchone()
                    self.lastrowid = row[0] if row else None
                except Exception:
                    self.lastrowid = None
        except Exception as e:
            logger.error(f"PG execute failed: {e} | SQL: {sql[:200]}")
            raise
        return self

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]):
        self._c.executemany(self._translate(sql), seq_of_params)
        return self

    def fetchone(self):
        row = self._c.fetchone()
        if row is None:
            return None
        return _PgRow(self._c, row)

    def fetchall(self) -> List[_PgRow]:
        rows = self._c.fetchall()
        return [_PgRow(self._c, r) for r in rows]

    @property
    def rowcount(self) -> int:
        return self._c.rowcount

    def close(self):
        self._c.close()


class _PgConnectionShim:
    """sqlite3.Connection-compatible wrapper around psycopg2."""

    def __init__(self, pg_conn):
        self._conn = pg_conn
        self._conn.autocommit = False

    def cursor(self):
        return _PgCursor(self._conn.cursor())

    def execute(self, sql: str, params: Sequence[Any] = ()):
        # Mirrors sqlite3.Connection.execute
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


# ------------------------------------------------------------------ #
# Public factory
# ------------------------------------------------------------------ #
_lock = threading.Lock()


def get_connection(database_url: Optional[str] = None):
    """Return a connection object usable by the existing DatabaseManager."""
    url = database_url or os.getenv(
        "DATABASE_URL", "sqlite:///exam_platform.db"
    )

    if is_sqlite_url(url):
        conn = sqlite3.connect(sqlite_path(url), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    if is_postgres_url(url):
        if not _pg_available:
            raise RuntimeError(
                "DATABASE_URL points at Postgres but psycopg2 is not installed. "
                "Run: pip install psycopg2-binary"
            )
        pg_conn = psycopg2.connect(url)
        return _PgConnectionShim(pg_conn)

    raise ValueError(f"Unsupported DATABASE_URL scheme: {url}")


def driver_name(database_url: Optional[str] = None) -> str:
    url = database_url or os.getenv(
        "DATABASE_URL", "sqlite:///exam_platform.db"
    )
    if is_postgres_url(url):
        return "postgres"
    return "sqlite"
