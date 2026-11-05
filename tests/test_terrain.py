import math

import pandas as pd

from nexttrip.config import FARE_MATRIX_CPM_CSV, FARE_MATRIX_CSV
from nexttrip.terrain import (
    cheapest_per_destination,
    fare_matrix_pivot,
    load_cpm_ranking,
    load_fare_matrix,
)


def test_load_fare_matrix_bundled_rows():
    df = load_fare_matrix(FARE_MATRIX_CSV)
    assert len(df) == 198  # 9 出発国 × 22 到着国の対象セル（表示圏外は行自体がない分を除く）
    assert set(df["origin"]) == {"JP", "KR", "CN", "VN", "TH", "PH", "IN", "SG", "MY"}


def test_fare_matrix_pivot_shape_and_known_cells():
    pivot = fare_matrix_pivot(load_fare_matrix(FARE_MATRIX_CSV))
    assert list(pivot.index) == ["JP", "KR", "CN", "VN", "TH", "PH", "IN", "SG", "MY"]
    assert pivot.shape[1] == 22
    assert pivot.loc["JP", "UK"] == 53294
    assert pivot.loc["CN", "TR"] == 29602
    assert pivot.loc["PH", "UAE"] == 19950  # $133 × ¥150
    # VN 発は対象月の表示70か国圏外のため US/CA/MX が欠測（便なしではない）
    assert math.isnan(pivot.loc["VN", "US"])


def test_cheapest_per_destination():
    pivot = fare_matrix_pivot(load_fare_matrix(FARE_MATRIX_CSV))
    cheapest = cheapest_per_destination(pivot)
    assert cheapest["UK"] == pivot["UK"].min()
    assert cheapest["UK"] == 27300  # IN 発ロンドン $182 × ¥150


def test_load_cpm_ranking_top_cell():
    df = load_cpm_ranking(FARE_MATRIX_CPM_CSV)
    top = df.iloc[0]
    assert top["origin_city"] == "MNL"
    assert top["destination_city"] == "DXB"
    assert top["cpm_jpy_per_mile"] == 4.65
    # CPM 昇順に並ぶ
    assert df["cpm_jpy_per_mile"].is_monotonic_increasing


def test_fare_matrix_pivot_handles_partial_frame():
    df = pd.DataFrame(
        [
            {"origin": "JP", "destination": "UK", "cheapest_city": "London",
             "price": 1, "currency": "JPY", "price_jpy_approx": 100},
            {"origin": "JP", "destination": "US", "cheapest_city": "Honolulu",
             "price": 1, "currency": "JPY", "price_jpy_approx": 50},
            {"origin": "KR", "destination": "UK", "cheapest_city": "London",
             "price": 1, "currency": "JPY", "price_jpy_approx": 80},
        ]
    )
    pivot = fare_matrix_pivot(df)
    assert pivot.loc["JP", "UK"] == 100
    assert math.isnan(pivot.loc["KR", "US"])
