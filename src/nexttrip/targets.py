from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_TARGET_COUNTRY_CODES = frozenset(
    """
AD AE AF AG AL AM AO AR AT AU AZ BA BB BD BE BF BG BH BI BJ BN BO BR BS BT BW BY BZ
CA CD CF CG CH CI CL CM CN CO CR CU CV CY CZ DE DJ DK DM DO DZ EC EE EG ER ES ET
FI FJ FM FR GA GB GD GE GH GM GN GQ GR GT GW GY HN HR HT HU ID IE IL IN IQ IR IS IT
JM JO JP KE KG KH KI KM KN KP KR KW KZ LA LB LC LI LK LR LS LT LU LV LY
MA MC MD ME MG MH MK ML MM MN MR MT MU MV MW MX MY MZ
NA NE NG NI NL NO NP NR NZ OM PA PE PG PH PK PL PS PT PW PY QA RO RS RU RW
SA SB SC SD SE SG SI SK SL SM SN SO SR SS ST SV SY SZ TD TG TH TJ TL TM TN TO TR TT
TV TW TZ UA UG US UY UZ VA VC VE VN VU WS XK YE ZA ZM ZW
""".split()
)


def load_target_country_codes(csv_path: Path) -> frozenset[str]:
    df = pd.read_csv(csv_path, dtype={"code": str}, keep_default_na=False)
    if "code" not in df.columns:
        raise ValueError("target_countries.csv に code 列が必要です")
    codes = [str(c).strip().upper() for c in df["code"].tolist() if str(c).strip()]
    if len(codes) != len(set(codes)):
        raise ValueError("target_countries.csv に重複した code があります")
    loaded = frozenset(codes)
    if loaded != DEFAULT_TARGET_COUNTRY_CODES:
        missing = DEFAULT_TARGET_COUNTRY_CODES - loaded
        extra = loaded - DEFAULT_TARGET_COUNTRY_CODES
        raise ValueError(
            "target_countries.csv が正準リストと一致しません。"
            f" missing={sorted(missing)} extra={sorted(extra)}"
        )
    return loaded
