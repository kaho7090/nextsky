from pathlib import Path

import pandas as pd

from nexttrip.db import connect, init_schema

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


RISK_TRENDS = ("", "up", "down", "flat")


def load_risk_watch_csv(csv_path: Path) -> pd.DataFrame:
    """高リスク国ウォッチ（Lv・トレンド）の同梱 CSV を読み込む。

    level は未評価なら空欄（None）。trend は '', 'up', 'down', 'flat' のいずれか。
    """
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    required = {"code", "level", "trend", "note", "updated"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"risk_watch.csv に必須列がありません: {sorted(missing)}")
    df = df.copy()
    df["code"] = df["code"].str.strip().str.upper()
    df = df.drop_duplicates(subset=["code"]).sort_values("code").reset_index(drop=True)

    def _parse_level(raw: str, code: str) -> int | None:
        raw = raw.strip()
        if raw == "":
            return None
        try:
            level = int(raw)
        except ValueError:
            raise ValueError(f"risk_watch.csv の level が整数ではありません: {code}={raw!r}") from None
        if level < 1 or level > 5:
            raise ValueError(f"risk_watch.csv の level は 1 から 5 です: {code}={level}")
        return level

    parsed_levels = [_parse_level(raw, code) for raw, code in zip(df["level"], df["code"])]
    # None を NaN に化けさせないため object 型で保持する
    df["level"] = pd.Series(parsed_levels, dtype=object, index=df.index)
    df["trend"] = df["trend"].str.strip()
    bad_trends = sorted(set(df["trend"]) - set(RISK_TRENDS))
    if bad_trends:
        raise ValueError(f"risk_watch.csv の trend が不正です: {bad_trends}")
    df["note"] = df["note"].str.strip()
    df["updated"] = df["updated"].str.strip()
    return df


def seed_risk_watch(conn, df: pd.DataFrame) -> int:
    """ウォッチデータを CSV から投入。既存行は全列を更新する。"""
    inserted = 0
    for row in df.itertuples(index=False):
        cur = conn.execute(
            """
            INSERT INTO risk_watch (country_code, level, trend, note, updated)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(country_code) DO UPDATE SET
                level = excluded.level,
                trend = excluded.trend,
                note = excluded.note,
                updated = excluded.updated
            """,
            (row.code, row.level, row.trend, row.note, row.updated),
        )
        if cur.rowcount == 1:
            inserted += 1
    conn.commit()
    return inserted


def ensure_database(
    db_path: Path,
    csv_path: Path,
    risk_watch_csv_path: Path | None = None,
) -> None:
    df = load_countries_csv(csv_path)
    with connect(db_path) as conn:
        init_schema(conn)
        seed_countries(conn, df)
        seed_supplemental_countries(conn)
        if risk_watch_csv_path is not None and risk_watch_csv_path.exists():
            seed_risk_watch(conn, load_risk_watch_csv(risk_watch_csv_path))
