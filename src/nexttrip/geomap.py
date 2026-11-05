from __future__ import annotations

import json
from enum import IntEnum
from pathlib import Path
from typing import Any

import plotly.graph_objects as go

from nexttrip.targets import DEFAULT_TARGET_COUNTRY_CODES

# Natural Earth の ADM0_A3 など、ISO-A2 が無い地物向け
ADM0_A3_TO_APP_CODE: dict[str, str] = {
    "KOS": "XK",
}


class MapStatus(IntEnum):
    OUT_OF_TARGET = 0
    UNVISITED = 1
    VISITED = 2


def normalize_geo_properties_to_app_code(properties: dict[str, Any]) -> str | None:
    """GeoJSON 特徴量のプロパティをアプリの2文字国コードに正規化する。"""
    for key in ("ISO_A2_EH", "ISO_A2"):
        value = properties.get(key)
        if value and value != "-99" and len(str(value)) == 2:
            return str(value).upper()
    adm0 = properties.get("ADM0_A3")
    if adm0 and adm0 in ADM0_A3_TO_APP_CODE:
        return ADM0_A3_TO_APP_CODE[adm0]
    return None


def _load_geojson_with_app_codes(geojson_path: Path) -> dict[str, Any]:
    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    for feature in data.get("features", []):
        props = feature.setdefault("properties", {})
        app_code = normalize_geo_properties_to_app_code(props)
        if not app_code:
            app_code = f"_NE_{props.get('ADM0_A3', 'UNK')}"
        props["app_code"] = app_code
    return data


def resolve_target_codes_on_geojson(
    geojson_path: Path,
    target_codes: frozenset[str] = DEFAULT_TARGET_COUNTRY_CODES,
) -> dict[str, str]:
    """
    各対象国コードが GeoJSON 上のいずれかの地物に紐づくことを検証し、
    代表地物名（Natural Earth の NAME）を返す。
    """
    data = _load_geojson_with_app_codes(geojson_path)
    code_to_name: dict[str, str] = {}
    for feature in data["features"]:
        props = feature["properties"]
        app_code = props.get("app_code")
        if not app_code:
            continue
        name = props.get("NAME") or props.get("ADMIN") or app_code
        code_to_name.setdefault(app_code, name)

    missing = sorted(target_codes - set(code_to_name))
    if missing:
        raise ValueError(
            "GeoJSON に対応地物が見つからない対象国があります: "
            f"{missing}"
        )
    return {code: code_to_name[code] for code in target_codes}


def status_for_country(
    code: str,
    target_codes: frozenset[str],
    visited: bool,
) -> MapStatus:
    if code not in target_codes:
        return MapStatus.OUT_OF_TARGET
    return MapStatus.VISITED if visited else MapStatus.UNVISITED


def build_country_status_lookup(
    records: list[dict[str, Any]],
    target_codes: frozenset[str],
) -> dict[str, MapStatus]:
    lookup: dict[str, MapStatus] = {}
    for row in records:
        code = str(row["code"]).upper()
        visited = bool(int(row.get("visited", 0)))
        lookup[code] = status_for_country(code, target_codes, visited)
    for code in target_codes:
        lookup.setdefault(code, MapStatus.UNVISITED)
    return lookup


def build_world_map_figure(
    records: list[dict[str, Any]],
    target_codes: frozenset[str],
    geojson_path: Path,
) -> go.Figure:
    resolve_target_codes_on_geojson(geojson_path, target_codes)
    geojson = _load_geojson_with_app_codes(geojson_path)
    status_lookup = build_country_status_lookup(records, target_codes)
    name_ja = {str(r["code"]).upper(): r["name_ja"] for r in records}
    name_en = {str(r["code"]).upper(): r["name_en"] for r in records}
    visited_lookup = {
        str(r["code"]).upper(): bool(int(r.get("visited", 0))) for r in records
    }
    priority_lookup = {
        str(r["code"]).upper(): int(r.get("priority", 0)) for r in records
    }

    code_status: dict[str, MapStatus] = {}
    code_props: dict[str, dict[str, Any]] = {}
    for feature in geojson["features"]:
        props = feature["properties"]
        code = str(props["app_code"]).upper()
        code_props.setdefault(code, props)
        if code in target_codes:
            code_status[code] = status_lookup.get(code, MapStatus.UNVISITED)
        else:
            code_status[code] = MapStatus.OUT_OF_TARGET

    locations = sorted(code_status.keys())
    z_values = [float(code_status[c]) for c in locations]
    hover_texts: list[str] = []
    for code in locations:
        props = code_props[code]
        ja = name_ja.get(code, props.get("NAME", ""))
        en = name_en.get(code, props.get("NAME", ""))
        in_target = code in target_codes
        target_label = "対象" if in_target else "対象外"
        if in_target:
            visit_label = "訪問済み" if visited_lookup.get(code, False) else "未訪問"
            priority = priority_lookup.get(code, 0)
            hover = (
                f"<b>{ja}</b><br>英語名: {en}<br>"
                f"コード: {code}<br>{target_label}<br>"
                f"訪問: {visit_label}<br>優先度: {priority}"
            )
        else:
            hover = (
                f"<b>{ja or en or props.get('NAME', '')}</b><br>"
                f"英語名: {en or props.get('NAME', '')}<br>"
                f"コード: {code}<br>{target_label}"
            )
        hover_texts.append(hover)

    fig = go.Figure(
        go.Choropleth(
            geojson=geojson,
            locations=locations,
            z=z_values,
            customdata=hover_texts,
            featureidkey="properties.app_code",
            hovertemplate="%{customdata}<extra></extra>",
            colorscale=[
                [0.0, "#BDBDBD"],
                [0.33, "#BDBDBD"],
                [0.34, "#5C9BD5"],
                [0.66, "#5C9BD5"],
                [0.67, "#3D8B5F"],
                [1.0, "#3D8B5F"],
            ],
            zmin=0,
            zmax=2,
            showscale=False,
        )
    )
    fig.update_geos(
        showframe=False,
        showcoastlines=True,
        projection_type="natural earth",
        bgcolor="rgba(0,0,0,0)",
        fitbounds="locations",
        visible=True,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=520,
        title="世界地図（訪問状況）",
    )
    return fig
