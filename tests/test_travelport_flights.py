import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from nextsky.flights.config import TravelportSettings, load_travelport_settings
from nextsky.flights.exceptions import (
    FlightSearchApiError,
    FlightSearchAuthError,
    FlightSearchConfigError,
    FlightSearchTransportError,
)
from nextsky.flights.models import FlightSearchParams
from nextsky.flights.travelport.auth import TravelportTokenProvider
from nextsky.flights.travelport.client import TravelportSearchClient
from nextsky.flights.travelport.parser import parse_search_response
from nextsky.flights.travelport.provider import TravelportFlightSearchProvider
from nextsky.flights.travelport.requests import build_catalog_search_payload

FIXTURE = Path(__file__).parent / "fixtures" / "travelport_search_with_fare_calc.json"


@pytest.fixture
def settings() -> TravelportSettings:
    return TravelportSettings(
        client_id="cid",
        client_secret="secret",
        username="user",
        password="pass",
        pcc="ABC1",
        access_group=None,
        gds_suffix="1G",
        auth_url="https://auth.example/oauth/token",
        api_base_url="https://api.example/11/air",
        timeout_seconds=5.0,
    )


def test_build_request_includes_gds_and_fare_calculation(settings: TravelportSettings):
    payload = build_catalog_search_payload(
        FlightSearchParams("NRT", "ICN", date(2026, 6, 1), adults=1),
        settings,
    )
    req = payload["CatalogProductOfferingsRequest"]
    assert req["contentSourceList"] == ["GDS"]
    assert req["CustomResponseModifiersAir"]["includeFareCalculationInd"] is True
    assert req["PricingModifiersAir"]["PricingPCC"] == "ABC1"


def test_parse_fare_calculation_from_fixture():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    offers = parse_search_response(data)
    assert len(offers) == 1
    offer = offers[0]
    assert offer.fare_calculation_available is True
    assert "TYO NH SEL" in (offer.fare_calculation or "")
    assert offer.fare_basis_codes == ["YOWJP"]
    assert offer.currency == "JPY"
    assert offer.base_fare == 45000.0
    assert offer.total_taxes == 5200.0
    assert any(t.code == "YQ" for t in offer.surcharge_lines)


def test_parse_without_fare_calculation():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    breakdown = data["CatalogProductOfferingsResponse"]["CatalogProductOfferings"][
        "CatalogProductOffering"
    ][0]["ProductBrandOptions"][0]["ProductBrandOffering"][0]["BestCombinablePrice"][
        "PriceBreakdown"
    ][0]
    del breakdown["FareCalculation"]
    offers = parse_search_response(data)
    assert offers[0].fare_calculation_available is False
    assert offers[0].fare_calculation is None


def test_missing_env_raises_config_error(monkeypatch):
    monkeypatch.delenv("TRAVELPORT_CLIENT_ID", raising=False)
    with pytest.raises(FlightSearchConfigError):
        load_travelport_settings()


def test_auth_failure(settings: TravelportSettings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = TravelportTokenProvider(settings, client=client)
    with pytest.raises(FlightSearchAuthError):
        provider.get_token()


def test_search_http_error(settings: TravelportSettings):
    def handler(request: httpx.Request) -> httpx.Response:
        if "oauth" in request.url.path:
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        return httpx.Response(500, text="server error")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    token_provider = TravelportTokenProvider(settings, client=client)
    search_client = TravelportSearchClient(settings, token_provider, client=client)
    with pytest.raises(FlightSearchApiError) as exc:
        search_client.search_catalog(
            FlightSearchParams("NRT", "ICN", date(2026, 6, 1))
        )
    assert exc.value.status_code == 500


def test_search_timeout(settings: TravelportSettings):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, timeout=0.1)
    token_provider = TravelportTokenProvider(settings, client=client)
    with pytest.raises(FlightSearchTransportError):
        token_provider.get_token()


def test_empty_results(settings: TravelportSettings):
    payload = {"CatalogProductOfferingsResponse": {"CatalogProductOfferings": {}}}
    assert parse_search_response(payload) == []


def test_provider_search_with_mock(settings: TravelportSettings):
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        if "oauth" in request.url.path:
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        return httpx.Response(200, json=fixture)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    token_provider = TravelportTokenProvider(settings, client=client)
    search_client = TravelportSearchClient(settings, token_provider, client=client)
    provider = TravelportFlightSearchProvider(settings=settings, client=search_client)
    offers = provider.search(FlightSearchParams("NRT", "ICN", date(2026, 6, 1)))
    assert len(offers) == 1
    assert offers[0].fare_calculation_available
