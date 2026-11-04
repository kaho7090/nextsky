from __future__ import annotations

from nextsky.flights.config import TravelportSettings, load_travelport_settings
from nextsky.flights.models import FlightOffer, FlightSearchParams
from nextsky.flights.travelport.auth import TravelportTokenProvider
from nextsky.flights.travelport.client import TravelportSearchClient
from nextsky.flights.travelport.parser import parse_search_response


class TravelportFlightSearchProvider:
    def __init__(
        self,
        settings: TravelportSettings | None = None,
        client: TravelportSearchClient | None = None,
    ) -> None:
        self._settings = settings or load_travelport_settings()
        if client is None:
            token_provider = TravelportTokenProvider(self._settings)
            client = TravelportSearchClient(self._settings, token_provider)
        self._client = client

    def search(self, params: FlightSearchParams) -> list[FlightOffer]:
        payload = self._client.search_catalog(params)
        return parse_search_response(payload)
