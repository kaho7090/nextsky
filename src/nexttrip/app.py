"""Streamlit UI（日本語）。"""

import sqlite3

import pandas as pd
import streamlit as st

from nexttrip.config import (
    CASES_JSON,
    COUNTRIES_CSV,
    DEFAULT_DB_PATH,
    FARE_MATRIX_CPM_CSV,
    FARE_MATRIX_CSV,
    GEOJSON_COUNTRIES_PATH,
    RISK_WATCH_CSV,
    TARGET_COUNTRIES_CSV,
)
from nexttrip.cases import load_cases
from nexttrip.dataset import ensure_database
from nexttrip.geomap import build_world_map_figure
from nexttrip.ranking import rank_unvisited
from nexttrip.terrain import (
    cheapest_per_destination,
    fare_matrix_pivot,
    load_cpm_ranking,
    load_fare_matrix,
)
from nexttrip.repository import list_countries_with_preferences, set_priority, set_visited
from nexttrip.flights.env_loader import load_project_dotenv
from nexttrip.flights.ui import render_flights_tab
from nexttrip.targets import load_target_country_codes

st.set_page_config(page_title="NextTrip", page_icon="🌍", layout="wide")


@st.cache_resource
def get_connection(db_path: str) -> sqlite3.Connection:
    ensure_database(DEFAULT_DB_PATH, COUNTRIES_CSV, RISK_WATCH_CSV)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@st.cache_data
def get_target_codes() -> frozenset[str]:
    return load_target_country_codes(TARGET_COUNTRIES_CSV)


@st.cache_data
def get_cases() -> list[dict]:
    return load_cases(CASES_JSON)


@st.cache_data
def get_fare_matrix() -> pd.DataFrame:
    return load_fare_matrix(FARE_MATRIX_CSV)


@st.cache_data
def get_cpm_ranking() -> pd.DataFrame:
    return load_cpm_ranking(FARE_MATRIX_CPM_CSV)


def _country_label(row: pd.Series) -> str:
    return f"{row['name_ja']} ({row['name_en']}) [{row['code']}]"


def render_cases_section() -> None:
    st.subheader("ケース集（エラー運賃・特殊運賃の検証記録）")
    st.caption(
        "出典：NextTicket エラー運賃ケース集（2026-11-05 時点）から公開分を抜粋。"
        "判定ラベルと到達ステージはケース集の原文どおりで、推測による格上げはしていません。"
    )
    for case in get_cases():
        verdict = case.get("verdict")
        badge = f"　判定：**{verdict}**" if verdict else ""
        hearsay = "（伝聞）" if case.get("hearsay") else ""
        st.markdown(f"### {case['id']} {case['title']}{badge}")
        st.markdown(
            f"- 観測：{case.get('observed', '')}／{case.get('source_type', '')}{hearsay}\n"
            f"- ルート：{case.get('route', '')}\n"
            f"- 価格：{case.get('price', '')}"
        )
        if case.get("breakdown"):
            st.markdown(f"- 内訳：{case['breakdown']}")
        if case.get("channel"):
            st.markdown(f"- チャネル：{case['channel']}")
        st.markdown(f"- 到達ステージ：{case.get('stage', '')}")
        if case.get("structure"):
            st.write(case["structure"])
        if case.get("result"):
            st.markdown(f"- 結果・備考：{case['result']}")


def render_matrix_section() -> None:
    st.subheader("運賃マトリクス（アジア発・国別最安、片道）")
    st.caption(
        "2026-11-05 の Skyscanner Explore スナップショット（推定最安）です。"
        "予約可能な確定価格ではありません。セルは円換算の概算（USD 建てセルは ¥150 換算、"
        "JP/KR/CN 発は 2026年11月〜2027年2月の最安月、その他は対象月単月）。"
        "空欄はその月の表示圏外で、便がないとは限りません。黄色は到着国ごとの最安出発国です。"
    )
    pivot = fare_matrix_pivot(get_fare_matrix())
    cheapest = cheapest_per_destination(pivot)

    def _highlight(series: pd.Series) -> list[str]:
        if series.name not in cheapest:
            return [""] * len(series)
        return [
            "background-color: #fff3b0" if pd.notna(v) and v == cheapest[series.name] else ""
            for v in series
        ]

    styled = pivot.style.apply(_highlight, axis=0).format("{:,.0f}", na_rep="")
    st.dataframe(styled, use_container_width=True)

    st.markdown("#### CPM ランキング（主要セル、JPY/mile）")
    st.caption("運賃 ÷ 大圏距離（概算）。単価の掘り出し物は東南アジア発の長距離に集中しています。")
    cpm = get_cpm_ranking().rename(
        columns={
            "rank": "順位",
            "origin_city": "出発",
            "destination_city": "到着",
            "price_jpy": "価格（円）",
            "distance_mi": "距離（mi）",
            "cpm_jpy_per_mile": "CPM（円/mi）",
            "note": "備考",
        }
    )
    st.dataframe(cpm, use_container_width=True, hide_index=True)


def main() -> None:
    load_project_dotenv()
    st.title("NextTrip")
    st.caption("未訪問国を優先度付きでランキングし、旅の計画を支援します。")

    target_codes = get_target_codes()
    conn = get_connection(str(DEFAULT_DB_PATH))
    records = list_countries_with_preferences(conn)
    df = pd.DataFrame(records)
    df["code"] = df["code"].astype(str).str.upper()

    df_target = df[df["code"].isin(target_codes)].copy()
    visited_count = int((df_target["visited"] == 1).sum())
    total_targets = len(target_codes)
    st.metric("訪問済み / 対象国（197）", f"{visited_count} / {total_targets}")

    options = df_target.apply(_country_label, axis=1).tolist()
    code_by_label = dict(zip(options, df_target["code"]))

    tab_rank, tab_map, tab_visit, tab_priority, tab_flights, tab_cases = st.tabs(
        ["未訪問国ランキング", "世界地図", "訪問状況", "優先度の設定", "航空券検索", "ケース＆マトリクス"]
    )

    with tab_rank:
        st.subheader("未訪問国ランキング（197カ国対象）")
        watch_only = st.checkbox("ウォッチ対象国のみ（高リスク国ウォッチ）", value=False)
        ranked = rank_unvisited(df, target_codes=target_codes)
        if watch_only and "in_risk_watch" in ranked.columns:
            ranked = ranked[ranked["in_risk_watch"] == 1].reset_index(drop=True)
            ranked["rank"] = ranked.index + 1
        if ranked.empty:
            st.info("未訪問の対象国がありません。")
        else:
            display = ranked.copy()
            if "risk_trend" in display.columns:
                marks = {"up": "↑", "down": "↓", "flat": "→", "": ""}
                display["動向"] = display["risk_trend"].map(marks).fillna("")
            display = display.rename(
                columns={
                    "rank": "順位",
                    "code": "コード",
                    "name_ja": "国名（日本語）",
                    "name_en": "国名（英語）",
                    "priority": "優先度",
                    "risk_level": "リスクLv",
                    "risk_note": "ウォッチメモ",
                }
            )
            drop_cols = [c for c in ("risk_trend", "in_risk_watch") if c in display.columns]
            display = display.drop(columns=drop_cols)
            st.dataframe(display, use_container_width=True, hide_index=True)

    with tab_map:
        st.subheader("世界地図")
        st.markdown(
            "**凡例:** "
            "<span style='color:#3D8B5F'>■</span> 訪問済み（対象国）　"
            "<span style='color:#5C9BD5'>■</span> 未訪問（対象国）　"
            "<span style='color:#BDBDBD'>■</span> 対象外",
            unsafe_allow_html=True,
        )
        fig = build_world_map_figure(records, target_codes, GEOJSON_COUNTRIES_PATH)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("地図は閲覧専用です。訪問状況の変更は「訪問状況」タブから行ってください。")

    with tab_visit:
        st.subheader("訪問済みにする（197カ国）")
        current_visited = df_target[df_target["visited"] == 1]["code"].tolist()
        selected_labels = st.multiselect(
            "訪問済みの国",
            options=options,
            default=[
                lbl for lbl, code in code_by_label.items() if code in current_visited
            ],
        )
        if st.button("訪問状況を保存", type="primary"):
            selected_codes = {code_by_label[lbl] for lbl in selected_labels}
            for row in df_target.itertuples(index=False):
                set_visited(conn, row.code, row.code in selected_codes)
            st.success("訪問状況を保存しました。")
            st.rerun()

    with tab_priority:
        st.subheader("国ごとの優先度（0〜5）")
        st.write("訪問済みの国にも優先度を残せます。")
        label = st.selectbox(
            "国を選択",
            options=options,
            index=0,
        )
        code = code_by_label[label]
        current = int(df_target.loc[df_target["code"] == code, "priority"].iloc[0])
        priority = st.slider("優先度", min_value=0, max_value=5, value=current)
        if st.button("優先度を保存"):
            set_priority(conn, code, priority)
            st.success(f"{label} の優先度を {priority} に保存しました。")
            st.rerun()

    with tab_flights:
        unvisited_targets = [
            r
            for r in records
            if r["code"] in target_codes and not r["visited"]
        ]
        render_flights_tab(unvisited_targets)

    with tab_cases:
        render_cases_section()
        st.divider()
        render_matrix_section()


if __name__ == "__main__":
    main()
