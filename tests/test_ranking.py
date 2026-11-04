import pandas as pd

from nextsky.ranking import rank_unvisited


def test_rank_unvisited_excludes_visited_and_sorts():
    df = pd.DataFrame(
        [
            {"code": "JP", "name_en": "Japan", "name_ja": "日本", "visited": 1, "priority": 5},
            {"code": "US", "name_en": "United States", "name_ja": "米国", "visited": 0, "priority": 2},
            {"code": "FR", "name_en": "France", "name_ja": "フランス", "visited": 0, "priority": 4},
            {"code": "IS", "name_en": "Iceland", "name_ja": "アイスランド", "visited": 0, "priority": 4},
        ]
    )
    ranked = rank_unvisited(df, target_codes={"US", "FR", "IS", "JP"})
    assert list(ranked["code"]) == ["IS", "FR", "US"]


def test_non_target_countries_excluded_even_with_high_priority():
    df = pd.DataFrame(
        [
            {"code": "JP", "name_en": "Japan", "name_ja": "日本", "visited": 0, "priority": 1},
            {"code": "AQ", "name_en": "Antarctica", "name_ja": "南極", "visited": 0, "priority": 5},
        ]
    )
    ranked = rank_unvisited(df, target_codes={"JP"})
    assert list(ranked["code"]) == ["JP"]
    assert ranked.iloc[0]["rank"] == 1
