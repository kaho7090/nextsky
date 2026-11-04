import pytest

from nextsky.config import GEOJSON_COUNTRIES_PATH
from nextsky.geomap import (
    MapStatus,
    build_country_status_lookup,
    build_world_map_figure,
    normalize_geo_properties_to_app_code,
    resolve_target_codes_on_geojson,
    status_for_country,
)
from nextsky.targets import DEFAULT_TARGET_COUNTRY_CODES


def test_normalize_special_country_codes():
    assert normalize_geo_properties_to_app_code({"ISO_A2_EH": "TW", "ISO_A2": "CN-TW"}) == "TW"
    assert normalize_geo_properties_to_app_code({"ISO_A2_EH": "PS", "ISO_A2": "PS"}) == "PS"
    assert normalize_geo_properties_to_app_code({"ISO_A2_EH": "VA", "ISO_A2": "VA"}) == "VA"
    assert normalize_geo_properties_to_app_code({"ISO_A2_EH": "XK", "ISO_A2": "-99", "ADM0_A3": "KOS"}) == "XK"


def test_all_target_countries_resolve_on_geojson():
    resolved = resolve_target_codes_on_geojson(GEOJSON_COUNTRIES_PATH, DEFAULT_TARGET_COUNTRY_CODES)
    assert len(resolved) == 197
    assert set(resolved) == DEFAULT_TARGET_COUNTRY_CODES


def test_status_assignment_three_states():
    targets = frozenset({"JP", "US"})
    assert status_for_country("JP", targets, True) == MapStatus.VISITED
    assert status_for_country("US", targets, False) == MapStatus.UNVISITED
    assert status_for_country("FR", targets, False) == MapStatus.OUT_OF_TARGET


def test_build_country_status_lookup():
    records = [
        {"code": "JP", "name_ja": "日本", "name_en": "Japan", "visited": 1, "priority": 3},
        {"code": "US", "name_ja": "米国", "name_en": "United States", "visited": 0, "priority": 5},
        {"code": "AQ", "name_ja": "南極", "name_en": "Antarctica", "visited": 1, "priority": 5},
    ]
    lookup = build_country_status_lookup(records, frozenset({"JP", "US"}))
    assert lookup["JP"] == MapStatus.VISITED
    assert lookup["US"] == MapStatus.UNVISITED
    assert lookup["AQ"] == MapStatus.OUT_OF_TARGET


def test_build_world_map_figure():
    records = [
        {"code": "JP", "name_ja": "日本", "name_en": "Japan", "visited": 1, "priority": 3},
        {"code": "US", "name_ja": "米国", "name_en": "United States", "visited": 0, "priority": 2},
    ]
    fig = build_world_map_figure(records, DEFAULT_TARGET_COUNTRY_CODES, GEOJSON_COUNTRIES_PATH)
    assert len(fig.data) == 1


def test_missing_geojson_target_raises_clear_error(tmp_path):
    bad_geo = tmp_path / "bad.geojson"
    bad_geo.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="対応地物が見つからない"):
        resolve_target_codes_on_geojson(bad_geo, frozenset({"JP"}))
