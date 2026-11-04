from __future__ import annotations

import os
from typing import Protocol

from nextsky.flights.models import FlightOffer, FlightSearchParams
from nextsky.flights.travelport.provider import TravelportFlightSearchProvider


class FlightSearchProvider(Protocol):
    def search(self, params: FlightSearchParams) -> list[FlightOffer]:
        ...


def get_flight_search_provider() -> FlightSearchProvider:
    backend = os.getenv("FLIGHT_SEARCH_BACKEND", "travelport").lower()
    if backend == "travelport":
        return TravelportFlightSearchProvider()
    raise ValueError(f"未対応の FLIGHT_SEARCH_BACKEND: {backend}")
