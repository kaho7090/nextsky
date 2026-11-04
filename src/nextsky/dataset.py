from pathlib import Path

import pandas as pd

from nextsky.db import connect, init_schema

SUPPLEMENTAL_COUNTRIES = (
    {"code": "XK", "name_en": "Kosovo", "name_ja": "コソボ"},
)


def load_countries_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype={"code": str}, keep_default_na=False)
    required = {"code", "name_en", "name_ja"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"countries.csv に必須列がありません: {sorted(missing)}")
    df = df.drop_duplicates(subset=["code"]).sort_values("code").reset_index(drop=True)
    return df


def seed_countries(conn, df: pd.DataFrame) -> int:
    """国マスタを CSV から投入。既存行は name のみ更新。"""
    inserted = 0
    for row in df.itertuples(index=False):
        cur = conn.execute(
            """
            INSERT INTO countries (code, name_en, name_ja)
            VALUES (?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name_en = excluded.name_en,
                name_ja = excluded.name_ja
            """,
            (row.code, row.name_en, row.name_ja),
        )
        if cur.rowcount == 1:
            inserted += 1
    conn.commit()
    return inserted


def seed_supplemental_countries(conn, rows: tuple[dict[str, str], ...] = SUPPLEMENTAL_COUNTRIES) -> None:
    for row in rows:
        conn.execute(
            """
            INSERT INTO countries (code, name_en, name_ja)
            VALUES (?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name_en = excluded.name_en,
                name_ja = excluded.name_ja
            """,
            (row["code"], row["name_en"], row["name_ja"]),
        )
    conn.commit()


def ensure_database(db_path: Path, csv_path: Path) -> None:
    df = load_countries_csv(csv_path)
    with connect(db_path) as conn:
        init_schema(conn)
        seed_countries(conn, df)
        seed_supplemental_countries(conn)
