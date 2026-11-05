"""航空券検索 Streamlit UI（日本語）。"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from nexttrip.flights.env_loader import (
    load_project_dotenv,
    travelport_readiness_report,
    apply_travelport_env_from_mapping,
)

from nexttrip.flights.exceptions import (
    FlightSearchApiError,
    FlightSearchAuthError,
    FlightSearchConfigError,
    FlightSearchError,
    FlightSearchTransportError,
)
from nexttrip.flights.models import FlightSearchParams
from nexttrip.flights.provider import get_flight_search_provider


def _hydrate_travelport_env_from_streamlit_secrets() -> None:
    """secrets.toml が無い場合も例外でアプリを止めない。"""
    try:
        secrets = st.secrets  # type: ignore[attr-defined]
    except StreamlitSecretNotFoundError:
        return
    except Exception:
        return
    try:
        apply_travelport_env_from_mapping(secrets)
    except StreamlitSecretNotFoundError:
        return
    except Exception:
        return


def _render_travelport_config_status() -> bool:
    """設定状態を表示。ready のとき True（秘密値は表示しない）。"""
    report = travelport_readiness_report()
    if report["ready_for_api"]:
        st.success(
            "Travelport API の接続設定は揃っています。"
            " 検索ボタンでトライアル API に接続します。"
        )
        return True
    st.warning(
        "Travelport API の認証情報が未設定です。"
        " リポジトリルートの `.env` または `.streamlit/secrets.toml` を設定してください。"
    )
    for issue in report.get("issues", []):
        st.caption(issue)
    missing = [
        name
        for name, status in report.get("required_variables", {}).items()
        if status == "missing"
    ]
    if missing:
        st.caption("未設定の必須項目: " + ", ".join(missing))
    st.caption("テンプレートは `.env.example` を参照してください。")
    return False


_TREND_MARKS = {"up": "↑", "down": "↓", "flat": "→", "": ""}


def target_country_label(country: dict) -> str:
    return f"{country['name_ja']} ({country['name_en']}) [{country['code']}]"


def target_country_context(country: dict) -> str:
    """対象国のウォッチ文脈（Lv・動向・メモ）を1行で返す。ウォッチ外なら空文字。"""
    if not country.get("in_risk_watch"):
        return ""
    parts: list[str] = []
    level = country.get("risk_level")
    if level is not None:
        parts.append(f"リスクLv.{level}")
    mark = _TREND_MARKS.get(str(country.get("risk_trend") or ""), "")
    if mark:
        parts.append(f"動向 {mark}")
    note = str(country.get("risk_note") or "").strip()
    if note:
        parts.append(note)
    return " / ".join(parts)


def _render_target_country_picker(countries: list[dict]) -> None:
    st.markdown("**対象国（未訪問）から探す**")
    labels = ["（未選択）"] + [target_country_label(c) for c in countries]
    by_label = {target_country_label(c): c for c in countries}
    selected = st.selectbox("対象国", options=labels, index=0, key="fare_target_label")
    if selected == "（未選択）":
        st.session_state.pop("fare_target_country", None)
        return
    country = by_label[selected]
    st.session_state["fare_target_country"] = country["code"]
    context = target_country_context(country)
    if context:
        st.warning(f"ウォッチ情報: {context}")
    st.caption(
        f"目的地（IATA）には {country['name_ja']} の主要空港コードを入力してください。"
    )


def render_flights_tab(countries: list[dict] | None = None) -> None:
    load_project_dotenv()
    _hydrate_travelport_env_from_streamlit_secrets()
    st.subheader("航空券検索（片道・Travelport トライアル）")
    st.caption(
        "GDS コンテンツを対象に検索します。"
        " Fare Calculation の取得は `includeFareCalculationInd=true` で要求します。"
    )
    _render_travelport_config_status()
    if countries:
        _render_target_country_picker(countries)

    with st.form("flight_search_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            origin = st.text_input("出発地（IATA）", value="NRT", max_chars=3).strip().upper()
        with col2:
            destination = st.text_input("目的地（IATA）", value="ICN", max_chars=3).strip().upper()
        with col3:
            adults = st.number_input("大人", min_value=1, max_value=9, value=1, step=1)
        departure = st.date_input(
            "出発日",
            value=date.today() + timedelta(days=30),
            min_value=date.today(),
        )
        submitted = st.form_submit_button("検索", type="primary")

    if not submitted:
        return

    if len(origin) != 3 or len(destination) != 3:
        st.error("出発地・目的地は3文字の IATA 空港コードで入力してください。")
        return

    params = FlightSearchParams(
        origin=origin,
        destination=destination,
        departure_date=departure,
        adults=int(adults),
    )

    try:
        provider = get_flight_search_provider()
        offers = provider.search(params)
    except FlightSearchConfigError as exc:
        st.warning(str(exc))
        return
    except FlightSearchAuthError as exc:
        st.error(str(exc))
        return
    except FlightSearchApiError as exc:
        st.error(str(exc))
        return
    except FlightSearchTransportError as exc:
        st.error(str(exc))
        return
    except FlightSearchError as exc:
        st.error(str(exc))
        return

    if not offers:
        st.info("条件に一致する便は見つかりませんでした。")
        return

    st.success(f"{len(offers)} 件の候補を取得しました。")
    for idx, offer in enumerate(offers, start=1):
        title = " / ".join(
            part
            for part in [
                offer.carrier,
                ", ".join(offer.flight_numbers) if offer.flight_numbers else None,
                f"{offer.origin}→{offer.destination}",
            ]
            if part
        )
        with st.expander(f"{idx}. {title or offer.offer_id}", expanded=idx == 1):
            st.write(
                f"**出発:** {offer.departure_time or '—'}  "
                f"**到着:** {offer.arrival_time or '—'}  "
                f"**乗継:** {offer.stops if offer.stops is not None else '—'} 回"
            )
            st.write(
                f"**通貨:** {offer.currency or '—'}  "
                f"**基本運賃:** {offer.base_fare if offer.base_fare is not None else '—'}  "
                f"**税金:** {offer.total_taxes if offer.total_taxes is not None else '—'}  "
                f"**合計:** {offer.total_price if offer.total_price is not None else '—'}"
            )
            if offer.fare_basis_codes:
                st.write("**Fare Basis:** " + ", ".join(offer.fare_basis_codes))
            else:
                st.write("**Fare Basis:** —")
            if offer.tax_breakdown:
                tax_text = ", ".join(
                    f"{t.code}:{t.amount}" for t in offer.tax_breakdown if t.code
                )
                st.write(f"**税内訳:** {tax_text or '—'}")
            if offer.surcharge_lines:
                st.write(
                    "**サーチャージ (YQ/YR):** "
                    + ", ".join(f"{t.code}:{t.amount}" for t in offer.surcharge_lines)
                )
            st.markdown("**Fare Calculation**")
            if offer.fare_calculation_available and offer.fare_calculation:
                st.code(offer.fare_calculation)
            else:
                st.info("この検索結果では Fare Calculation を取得できませんでした。")
