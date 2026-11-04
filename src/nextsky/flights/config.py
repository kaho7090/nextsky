from __future__ import annotations

import os
from dataclasses import dataclass

from nextsky.flights.exceptions import FlightSearchConfigError

REQUIRED_ENV_VARS = (
    "TRAVELPORT_CLIENT_ID",
    "TRAVELPORT_CLIENT_SECRET",
    "TRAVELPORT_USERNAME",
    "TRAVELPORT_PASSWORD",
    "TRAVELPORT_PCC",
)

DEFAULT_AUTH_URL = "https://auth.pp.travelport.net/oauth/token"
DEFAULT_API_BASE_URL = "https://api.pp.travelport.net/11/air"


@dataclass(frozen=True)
class TravelportSettings:
    client_id: str
    client_secret: str
    username: str
    password: str
    pcc: str
    access_group: str | None
    gds_suffix: str
    auth_url: str
    api_base_url: str
    timeout_seconds: float

    @property
    def search_url(self) -> str:
        base = self.api_base_url.rstrip("/")
        return f"{base}/catalog/search/catalogproductofferings"

    @property
    def tvp_pcc_core(self) -> str:
        return f"{self.pcc}_{self.gds_suffix}"


def load_travelport_settings() -> TravelportSettings:
    from nextsky.flights.env_loader import load_project_dotenv

    load_project_dotenv()
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        raise FlightSearchConfigError(
            "Travelport API の認証情報が不足しています。"
            f" 未設定: {', '.join(missing)}。"
            " `.env.example` を参照し、環境変数または Streamlit secrets に設定してください。"
        )
    return TravelportSettings(
        client_id=os.environ["TRAVELPORT_CLIENT_ID"],
        client_secret=os.environ["TRAVELPORT_CLIENT_SECRET"],
        username=os.environ["TRAVELPORT_USERNAME"],
        password=os.environ["TRAVELPORT_PASSWORD"],
        pcc=os.environ["TRAVELPORT_PCC"],
        access_group=os.getenv("TRAVELPORT_ACCESS_GROUP"),
        gds_suffix=os.getenv("TRAVELPORT_GDS_SUFFIX", "1G"),
        auth_url=os.getenv("TRAVELPORT_AUTH_URL", DEFAULT_AUTH_URL),
        api_base_url=os.getenv("TRAVELPORT_API_BASE_URL", DEFAULT_API_BASE_URL),
        timeout_seconds=float(os.getenv("TRAVELPORT_TIMEOUT_SECONDS", "60")),
    )
