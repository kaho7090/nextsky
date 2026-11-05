"""Streamlit UI（日本語）。"""

import sqlite3

import pandas as pd
import streamlit as st

from nexttrip.config import (
    COUNTRIES_CSV,
    DEFAULT_DB_PATH,
    GEOJSON_COUNTRIES_PATH,
    RISK_WATCH_CSV,
    TARGET_COUNTRIES_CSV,
)
from nexttrip.dataset import ensure_database
from nexttrip.geomap import build_world_map_figure
from nexttrip.ranking import rank_unvisited
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


def _country_label(row: pd.Series) -> str:
    return f"{row['name_ja']} ({row['name_en']}) [{row['code']}]"


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

    tab_rank, tab_map, tab_visit, tab_priority, tab_flights = st.tabs(
        ["未訪問国ランキング", "世界地図", "訪問状況", "優先度の設定", "航空券検索"]
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


if __name__ == "__main__":
    main()
