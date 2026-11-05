"""運賃マトリクス（アジア発・国別最安、片道）の読み込みと整形。

データは data/fare_matrix.csv（2026-11-05 の Skyscanner Explore
スナップショット）と、主要セルの CPM ランキング data/fare_matrix_cpm.csv。
価格は推定最安であり、予約可能な確定価格ではない。
"""

from pathlib import Path

import pandas as pd

ORIGIN_ORDER = ["JP", "KR", "CN", "VN", "TH", "PH", "IN", "SG", "MY"]
DESTINATION_ORDER = [
    "UK", "IE", "FR", "IT", "ES", "CH", "DE", "DK", "SE", "NO", "FI",
    "PL", "CZ", "HU", "AT", "TR", "UAE", "QA", "OM", "US", "CA", "MX",
]


def load_fare_matrix(csv_path: Path) -> pd.DataFrame:
    """ロング形式（origin × destination の最安行）のマトリクスを読む。"""
    df = pd.read_csv(csv_path)
    required = {"origin", "destination", "cheapest_city", "price", "currency", "price_jpy_approx"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"fare matrix is missing columns: {sorted(missing)}")
    df["price_jpy_approx"] = pd.to_numeric(df["price_jpy_approx"], errors="raise")
    return df


def fare_matrix_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """出発国 × 到着国の円換算最安（price_jpy_approx）ピボットを返す。

    対象月の Explore 表示に現れなかった組合せは NaN（便なしとは限らない）。
    """
    pivot = df.pivot_table(
        index="origin", columns="destination", values="price_jpy_approx", aggfunc="min"
    )
    origins = [o for o in ORIGIN_ORDER if o in pivot.index]
    destinations = [d for d in DESTINATION_ORDER if d in pivot.columns]
    return pivot.reindex(index=origins, columns=destinations)


def cheapest_per_destination(pivot: pd.DataFrame) -> dict[str, float]:
    """到着国ごとに最も安い出発国の価格（円）を返す。"""
    return {col: float(pivot[col].min()) for col in pivot.columns if pivot[col].notna().any()}


def load_cpm_ranking(csv_path: Path) -> pd.DataFrame:
    """主要セルの CPM（JPY/mile、大圏距離・概算）ランキングを読む。"""
    df = pd.read_csv(csv_path)
    df["cpm_jpy_per_mile"] = pd.to_numeric(df["cpm_jpy_per_mile"], errors="raise")
    return df.sort_values("cpm_jpy_per_mile").reset_index(drop=True)
