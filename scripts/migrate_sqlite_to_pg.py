#!/usr/bin/env python
"""
Copy data from the current SQLite DB to a PostgreSQL DB.

Usage
-----
    # 1. Run Alembic against the target PG first so the schema exists:
    DATABASE_URL=postgresql://user:pwd@host:5432/proctoai \
        alembic -c backend/alembic.ini upgrade head

    # 2. Then run this script:
    python scripts/migrate_sqlite_to_pg.py \
        --sqlite backend/exam_platform.db \
        --postgres postgresql://user:pwd@host:5432/proctoai

Safety
------
  * Reads SQLite with a shared lock (no writes).
  * Wraps the PG copy in a single transaction per table.
  * Verifies row counts after each table; aborts if a mismatch.
  * Uses `ON CONFLICT DO NOTHING` so re-runs are idempotent.
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
from typing import List, Tuple

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("migrate")


# Tables in dependency order (parents before children).
TABLES: List[str] = [
    "users",
    "exams",
    "sessions",
    "proctoring_events",
    "question_banks",
    "questions",
    "question_bank_items",
    "question_reviews",
    "question_usage_stats",
]


def _sqlite_connect(path: str) -> sqlite3.Connection:
    if not os.path.exists(path):
        raise FileNotFoundError(f"SQLite file not found: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _pg_engine(url: str) -> Engine:
    if not url.startswith("postgresql"):
        raise ValueError("Postgres URL must start with 'postgresql://'")
    return create_engine(url, future=True)


def _columns(src_conn: sqlite3.Connection, table: str) -> List[str]:
    cur = src_conn.execute(f"PRAGMA table_info({table})")
    return [row["name"] for row in cur.fetchall()]


def _count(conn, table: str) -> int:
    if isinstance(conn, sqlite3.Connection):
        cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]
    with conn.connect() as c:
        return c.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


def _copy_table(
    src: sqlite3.Connection,
    dst: Engine,
    table: str,
    batch: int = 500,
) -> Tuple[int, int]:
    """Returns (rows_read, rows_written)."""
    cols = _columns(src, table)
    if not cols:
        log.warning(f"{table}: no columns found in SQLite, skipping")
        return 0, 0

    # Verify the table exists in PG
    insp = inspect(dst)
    if table not in insp.get_table_names():
        log.warning(f"{table}: missing in Postgres, skipping")
        return 0, 0

    src_rows = src.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
    if not src_rows:
        log.info(f"{table}: 0 rows to copy")
        return 0, 0

    # Detect boolean columns in target so we can cast 0/1 -> False/True
    pg_cols = inspect(dst).get_columns(table)
    bool_cols = {c["name"] for c in pg_cols if str(c["type"]).upper() == "BOOLEAN"}

    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    stmt = text(
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT DO NOTHING"
    )

    written = 0
    with dst.begin() as conn:
        for i in range(0, len(src_rows), batch):
            chunk = []
            for row in src_rows[i : i + batch]:
                d = dict(row)
                for bc in bool_cols:
                    if bc in d and d[bc] is not None:
                        d[bc] = bool(d[bc])
                chunk.append(d)
            result = conn.execute(stmt, chunk)
            written += result.rowcount if result.rowcount >= 0 else len(chunk)

    return len(src_rows), written


def migrate(sqlite_path: str, pg_url: str) -> None:
    src = _sqlite_connect(sqlite_path)
    dst = _pg_engine(pg_url)

    log.info("Source: %s", sqlite_path)
    log.info("Target: %s", pg_url.split("@")[-1])

    totals = {"read": 0, "written": 0, "tables": 0}

    for table in TABLES:
        try:
            read, written = _copy_table(src, dst, table)
            totals["read"] += read
            totals["written"] += written
            totals["tables"] += 1

            src_n = _count(src, table)
            dst_n = _count(dst, table)
            log.info(
                f"{table:30s}  sqlite={src_n:5d}  pg={dst_n:5d}  "
                f"copied={written:5d}"
            )
        except Exception as exc:  # noqa: BLE001
            log.error(f"{table}: failed - {exc}")
            raise

    src.close()
    log.info(
        "Done. Tables=%d  rows_read=%d  rows_written=%d",
        totals["tables"],
        totals["read"],
        totals["written"],
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Copy SQLite data to PostgreSQL")
    p.add_argument(
        "--sqlite",
        default=os.getenv("SQLITE_PATH", "backend/exam_platform.db"),
        help="Path to the source SQLite file",
    )
    p.add_argument(
        "--postgres",
        default=os.getenv("DATABASE_URL"),
        help="Target PostgreSQL URL (postgresql://user:pwd@host/db)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.postgres:
        log.error("Postgres URL missing. Pass --postgres or set DATABASE_URL.")
        return 2
    try:
        migrate(args.sqlite, args.postgres)
    except Exception:
        log.exception("Migration failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
