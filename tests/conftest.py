import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from nexttrip.db import init_schema
from nexttrip.dataset import seed_countries


@pytest.fixture
def sample_countries_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"code": "JP", "name_en": "Japan", "name_ja": "日本"},
            {"code": "US", "name_en": "United States", "name_ja": "米国"},
            {"code": "FR", "name_en": "France", "name_ja": "フランス"},
            {"code": "IS", "name_en": "Iceland", "name_ja": "アイスランド"},
        ]
    )


@pytest.fixture
def db_conn(tmp_path: Path, sample_countries_df: pd.DataFrame) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    seed_countries(conn, sample_countries_df)
    yield conn
    conn.close()
