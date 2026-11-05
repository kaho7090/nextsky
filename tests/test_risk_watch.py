from pathlib import Path

import pandas as pd
import pytest

from nexttrip.config import RISK_WATCH_CSV, TARGET_COUNTRIES_CSV
from nexttrip.dataset import ensure_database, load_risk_watch_csv, seed_risk_watch
from nexttrip.repository import list_countries_with_preferences
from nexttrip.targets import load_target_country_codes


def _write_csv(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "risk_watch.csv"
    path.write_text("code,level,trend,note,updated\n" + body, encoding="utf-8")
    return path


def test_load_risk_watch_csv_parses_level_and_trend(tmp_path: Path):
    path = _write_csv(tmp_path, "JP,3,up,メモ,2026-11-05\nFR,,,,2026-11-05\n")
    df = load_risk_watch_csv(path)
    by_code = {row.code: row for row in df.itertuples(index=False)}
    assert by_code["JP"].level == 3
    assert by_code["JP"].trend == "up"
    assert by_code["FR"].level is None
    assert by_code["FR"].trend == ""


def test_load_risk_watch_csv_rejects_out_of_range_level(tmp_path: Path):
    path = _write_csv(tmp_path, "JP,9,,,2026-11-05\n")
    with pytest.raises(ValueError):
        load_risk_watch_csv(path)


def test_load_risk_watch_csv_rejects_non_integer_level(tmp_path: Path):
    path = _write_csv(tmp_path, "JP,x,,,2026-11-05\n")
    with pytest.raises(ValueError):
        load_risk_watch_csv(path)


def test_load_risk_watch_csv_rejects_unknown_trend(tmp_path: Path):
    path = _write_csv(tmp_path, "JP,,sideways,,2026-11-05\n")
    with pytest.raises(ValueError):
        load_risk_watch_csv(path)


def test_seed_and_repository_join(db_conn):
    df = pd.DataFrame(
        [
            {"code": "JP", "level": 4, "trend": "down", "note": "悪化", "updated": "2026-11-05"},
        ]
    )
    seed_risk_watch(db_conn, df)
    records = {r["code"]: r for r in list_countries_with_preferences(db_conn)}
    assert records["JP"]["risk_level"] == 4
    assert records["JP"]["risk_trend"] == "down"
    assert records["JP"]["risk_note"] == "悪化"
    assert records["JP"]["in_risk_watch"] == 1
    assert records["US"]["risk_level"] is None
    assert records["US"]["in_risk_watch"] == 0


def test_ensure_database_seeds_risk_watch(tmp_path: Path, sample_countries_df):
    countries_path = tmp_path / "countries.csv"
    sample_countries_df.to_csv(countries_path, index=False)
    risk_path = _write_csv(tmp_path, "JP,2,flat,,2026-11-05\n")
    db_path = tmp_path / "app.db"
    ensure_database(db_path, countries_path, risk_path)

    import sqlite3

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT country_code, level, trend FROM risk_watch").fetchall()
    conn.close()
    assert rows == [("JP", 2, "flat")]


def test_bundled_risk_watch_csv_matches_targets():
    df = load_risk_watch_csv(RISK_WATCH_CSV)
    targets = load_target_country_codes(TARGET_COUNTRIES_CSV)
    assert set(df["code"]) <= set(targets)
    by_code = {row.code: row for row in df.itertuples(index=False)}
    # 枠組みで唯一の Lv.5 はマリ
    assert by_code["ML"].level == 5
