from __future__ import annotations

from typing import Any

import httpx

from nexttrip.flights.config import TravelportSettings
from nexttrip.flights.exceptions import FlightSearchApiError, FlightSearchTransportError
from nexttrip.flights.models import FlightSearchParams
from nexttrip.flights.travelport.auth import TravelportTokenProvider
from nexttrip.flights.travelport.requests import build_catalog_search_payload, build_search_headers


class TravelportSearchClient:
    def __init__(
        self,
        settings: TravelportSettings,
        token_provider: TravelportTokenProvider,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._token_provider = token_provider
        self._client = client

    def search_catalog(self, params: FlightSearchParams) -> dict[str, Any]:
        token = self._token_provider.get_token()
        headers = build_search_headers(token, self._settings)
        body = build_catalog_search_payload(params, self._settings)
        try:
            if self._client is not None:
                response = self._client.post(
                    self._settings.search_url,
                    headers=headers,
                    json=body,
                )
            else:
                with httpx.Client(timeout=self._settings.timeout_seconds) as client:
                    response = client.post(
                        self._settings.search_url,
                        headers=headers,
                        json=body,
                    )
        except httpx.TimeoutException as exc:
            raise FlightSearchTransportError("航空券検索がタイムアウトしました。") from exc
        except httpx.HTTPError as exc:
            raise FlightSearchTransportError("航空券検索の通信に失敗しました。") from exc

        if response.status_code != 200:
            raise FlightSearchApiError(
                f"Travelport 検索 API がエラーを返しました（HTTP {response.status_code}）。",
                status_code=response.status_code,
            )
        return response.json()
