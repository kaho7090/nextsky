import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS countries (
    code TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_ja TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_country_preferences (
    country_code TEXT PRIMARY KEY,
    visited INTEGER NOT NULL DEFAULT 0 CHECK (visited IN (0, 1)),
    priority INTEGER NOT NULL DEFAULT 0 CHECK (priority BETWEEN 0 AND 5),
    FOREIGN KEY (country_code) REFERENCES countries(code)
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()
