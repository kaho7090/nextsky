from pathlib import Path

import pandas as pd

from nextsky.config import COUNTRIES_CSV, TARGET_COUNTRIES_CSV
from nextsky.targets import DEFAULT_TARGET_COUNTRY_CODES, load_target_country_codes


def test_default_target_list_has_197_unique_codes():
    assert len(DEFAULT_TARGET_COUNTRY_CODES) == 197
    assert len(DEFAULT_TARGET_COUNTRY_CODES) == len(set(DEFAULT_TARGET_COUNTRY_CODES))


def test_target_csv_matches_canonical_list():
    loaded = load_target_country_codes(TARGET_COUNTRIES_CSV)
    assert loaded == DEFAULT_TARGET_COUNTRY_CODES


def test_all_target_codes_exist_in_country_master():
    master = pd.read_csv(COUNTRIES_CSV, dtype={"code": str}, keep_default_na=False)
    master_codes = {str(c).upper() for c in master["code"]}
    missing = sorted(DEFAULT_TARGET_COUNTRY_CODES - master_codes)
    assert missing == []


def test_country_master_not_reduced():
    master = pd.read_csv(COUNTRIES_CSV, dtype={"code": str})
    assert len(master) >= 249
