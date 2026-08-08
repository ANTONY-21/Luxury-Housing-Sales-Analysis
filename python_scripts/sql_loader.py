"""
sql_loader.py
=============
Step 2 of the Luxury Housing Sales Analysis pipeline.

Builds the warehouse: creates the schema, bulk-loads the cleaned CSV, creates
the analytics views, then runs every validation query and publishes the
results as markdown.

Backends
--------
SQLite is the default and needs nothing installed - the warehouse is a single
file at ``data/luxury_housing.db``. PostgreSQL and MySQL are supported through
SQLAlchemy; set ``DB_BACKEND`` in ``config.py`` or pass ``--backend``.

Run:
    python python_scripts/sql_loader.py
    python python_scripts/sql_loader.py --backend postgresql
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg  # noqa: E402

RESULTS_MD = cfg.OUTPUT_DIR / "sql_validation_results.md"
MAX_PRINT_ROWS = 20


# --------------------------------------------------------------------------
# SQL file helpers
# --------------------------------------------------------------------------
def _strip_comments(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("--")
    ).strip()


def split_statements(sql_text: str) -> list[str]:
    """
    Split a script into executable statements.

    Comments are stripped before splitting, not after - otherwise a semicolon
    inside a comment would split mid-comment and leave the tail behind as a
    bogus statement.
    """
    return [
        statement.strip()
        for statement in _strip_comments(sql_text).split(";")
        if statement.strip()
    ]


def parse_named_queries(path: Path) -> list[tuple[str, str]]:
    """Read a .sql file annotated with '-- name: <label>' into (label, sql) pairs."""
    queries: list[tuple[str, str]] = []
    label: str | None = None
    buffer: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*--\s*name:\s*(.+?)\s*$", line)
        if match:
            if label is not None:
                queries.append((label, _strip_comments("\n".join(buffer)).rstrip(";")))
            label, buffer = match.group(1), []
        elif label is not None:
            buffer.append(line)

    if label is not None:
        queries.append((label, _strip_comments("\n".join(buffer)).rstrip(";")))

    return [(name, sql) for name, sql in queries if sql.strip()]


# --------------------------------------------------------------------------
# Connection
# --------------------------------------------------------------------------
def create_connection(backend: str):
    """Return an open connection/engine for the requested backend."""
    if backend == "sqlite":
        cfg.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(cfg.SQLITE_PATH)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        print(f"    Connected to SQLite at {cfg.SQLITE_PATH}")
        return conn

    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:
        raise SystemExit(
            f"The '{backend}' backend needs SQLAlchemy plus a driver.\n"
            "  pip install sqlalchemy psycopg2-binary   # PostgreSQL\n"
            "  pip install sqlalchemy pymysql           # MySQL"
        ) from exc

    engine = create_engine(cfg.sqlalchemy_url(), future=True)
    with engine.connect() as probe:
        probe.execute(text("SELECT 1"))
    print(f"    Connected to {backend} at {cfg.DB_CONFIG['host']}:{cfg.DB_CONFIG['port']}")
    return engine


def run_script(conn, path: Path, backend: str) -> int:
    """Execute every statement in a .sql file."""
    statements = split_statements(path.read_text(encoding="utf-8"))
    if backend == "sqlite":
        cursor = conn.cursor()
        for statement in statements:
            cursor.execute(statement)
        conn.commit()
    else:
        from sqlalchemy import text
        with conn.begin() as tx:
            for statement in statements:
                tx.execute(text(statement))
    print(f"    Executed {len(statements)} statements from {path.name}")
    return len(statements)


# --------------------------------------------------------------------------
# Load
# --------------------------------------------------------------------------
def load_cleaned_data(path: Path = cfg.CLEANED_CSV) -> pd.DataFrame:
    """Read the cleaned CSV and lower-case the column names for SQL."""
    if not path.exists():
        raise SystemExit(
            f"Cleaned dataset not found at {path}.\n"
            "Run 'python python_scripts/data_cleaning.py' first."
        )
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    print(f"    Read {len(df):,} rows x {df.shape[1]} columns from {path.name}")
    return df


def insert_data(df: pd.DataFrame, conn, backend: str) -> None:
    """Bulk-insert the cleaned frame into the (already created) warehouse table."""
    if backend == "sqlite":
        # Default executemany keeps the bound-parameter count under SQLite's cap.
        df.to_sql(cfg.TABLE_NAME, conn, if_exists="append", index=False, chunksize=1000)
        conn.commit()
    else:
        df.to_sql(cfg.TABLE_NAME, conn, if_exists="append", index=False,
                  method="multi", chunksize=1000)
    print(f"    Inserted {len(df):,} rows into '{cfg.TABLE_NAME}'")


def read_sql(sql: str, conn) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def run_validation(conn) -> str:
    """Run every named query in validation_queries.sql and render the results."""
    queries = parse_named_queries(cfg.VALIDATION_SQL)
    sections = [
        "# SQL Validation Results",
        "",
        f"Backend: `{cfg.DB_BACKEND}` | Table: `{cfg.TABLE_NAME}` | "
        f"Queries run: {len(queries)}",
        "",
        "Generated by `python_scripts/sql_loader.py` from "
        "`sql_scripts/validation_queries.sql`.",
        "",
    ]

    for label, sql in queries:
        print(f"\n  {label}")
        print("  " + "-" * (len(label) + 2))
        result = read_sql(sql, conn)
        shown = result.head(MAX_PRINT_ROWS)
        printable = shown.to_string(index=False)
        print("    " + printable.replace("\n", "\n    "))
        if len(result) > MAX_PRINT_ROWS:
            print(f"    ... {len(result) - MAX_PRINT_ROWS} more rows")

        sections.extend([
            f"## {label}",
            "",
            "```sql",
            sql,
            "```",
            "",
            "```",
            printable,
            "```",
            "",
        ])

    return "\n".join(sections)


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------
def run(backend: str | None = None) -> None:
    backend = backend or cfg.DB_BACKEND
    cfg.DB_BACKEND = backend
    cfg.ensure_dirs()

    print("=" * 74)
    print(f"LUXURY HOUSING - SQL WAREHOUSE LOAD  (backend: {backend})")
    print("=" * 74)

    print("\n[1/5] Connecting...")
    conn = create_connection(backend)

    try:
        print("\n[2/5] Creating schema...")
        run_script(conn, cfg.SCHEMA_SQL, backend)

        print("\n[3/5] Loading cleaned data...")
        df = load_cleaned_data()
        insert_data(df, conn, backend)

        print("\n[4/5] Creating analytics views...")
        run_script(conn, cfg.VIEWS_SQL, backend)

        print("\n[5/5] Running validation queries...")
        markdown = run_validation(conn)
        RESULTS_MD.write_text(markdown, encoding="utf-8")

        print("\n" + "=" * 74)
        print("WAREHOUSE LOAD COMPLETE")
        print("=" * 74)
        if backend == "sqlite":
            print(f"  Database        : {cfg.SQLITE_PATH}")
        print(f"  Validation log  : {RESULTS_MD}")
    finally:
        conn.close() if backend == "sqlite" else conn.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load cleaned housing data into SQL.")
    parser.add_argument(
        "--backend",
        choices=["sqlite", "postgresql", "mysql"],
        default=cfg.DB_BACKEND,
        help="Warehouse backend (default: %(default)s)",
    )
    run(parser.parse_args().backend)


if __name__ == "__main__":
    main()
