from __future__ import annotations

import time
from typing import Any

import httpx

from nextsky.flights.config import TravelportSettings
from nextsky.flights.exceptions import FlightSearchAuthError, FlightSearchTransportError


class TravelportTokenProvider:
    def __init__(self, settings: TravelportSettings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        return self._fetch_token()

    def _fetch_token(self) -> str:
        data = {
            "grant_type": "password",
            "username": self._settings.username,
            "password": self._settings.password,
            "client_id": self._settings.client_id,
            "client_secret": self._settings.client_secret,
        }
        try:
            if self._client is not None:
                response = self._client.post(self._settings.auth_url, data=data)
            else:
                with httpx.Client(timeout=self._settings.timeout_seconds) as client:
                    response = client.post(self._settings.auth_url, data=data)
        except httpx.TimeoutException as exc:
            raise FlightSearchTransportError("認証リクエストがタイムアウトしました。") from exc
        except httpx.HTTPError as exc:
            raise FlightSearchTransportError("認証リクエストの通信に失敗しました。") from exc

        if response.status_code != 200:
            raise FlightSearchAuthError(
                f"Travelport 認証に失敗しました（HTTP {response.status_code}）。"
            )
        payload: dict[str, Any] = response.json()
        token = payload.get("access_token")
        if not token:
            raise FlightSearchAuthError("認証レスポンスに access_token が含まれていません。")
        expires_in = int(payload.get("expires_in", 86400))
        self._token = str(token)
        self._expires_at = time.time() + expires_in
        return self._token
