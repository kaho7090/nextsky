import sqlite3
from typing import Any


def _ensure_preference_row(conn: sqlite3.Connection, country_code: str) -> None:
    conn.execute(
        """
        INSERT INTO user_country_preferences (country_code, visited, priority)
        VALUES (?, 0, 0)
        ON CONFLICT(country_code) DO NOTHING
        """,
        (country_code,),
    )


def set_visited(conn: sqlite3.Connection, country_code: str, visited: bool) -> None:
    _ensure_preference_row(conn, country_code)
    conn.execute(
        "UPDATE user_country_preferences SET visited = ? WHERE country_code = ?",
        (1 if visited else 0, country_code),
    )
    conn.commit()


def set_priority(conn: sqlite3.Connection, country_code: str, priority: int) -> None:
    if priority < 0 or priority > 5:
        raise ValueError("優先度は 0 から 5 の整数です")
    _ensure_preference_row(conn, country_code)
    conn.execute(
        "UPDATE user_country_preferences SET priority = ? WHERE country_code = ?",
        (priority, country_code),
    )
    conn.commit()


def list_countries_with_preferences(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            c.code,
            c.name_en,
            c.name_ja,
            COALESCE(p.visited, 0) AS visited,
            COALESCE(p.priority, 0) AS priority
        FROM countries c
        LEFT JOIN user_country_preferences p ON p.country_code = c.code
        ORDER BY c.name_ja COLLATE NOCASE
        """
    ).fetchall()
    return [dict(row) for row in rows]
