from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from nexttrip.config import PROJECT_ROOT
from nexttrip.flights.config import (
    DEFAULT_API_BASE_URL,
    DEFAULT_AUTH_URL,
    REQUIRED_ENV_VARS,
    TravelportSettings,
    load_travelport_settings,
)
from nexttrip.flights.exceptions import FlightSearchConfigError

OPTIONAL_ENV_VARS = (
    "TRAVELPORT_ACCESS_GROUP",
    "TRAVELPORT_GDS_SUFFIX",
    "TRAVELPORT_AUTH_URL",
    "TRAVELPORT_API_BASE_URL",
    "TRAVELPORT_TIMEOUT_SECONDS",
)

_DOTENV_LOADED = False
_DOTENV_PATH: Path | None = None


def project_dotenv_path() -> Path:
    return PROJECT_ROOT / ".env"


def load_project_dotenv() -> bool:
    """
    リポジトリルートの `.env` を読み込む（存在する場合）。
    既に設定済みの環境変数は上書きしない（override=False）。
    """
    global _DOTENV_LOADED, _DOTENV_PATH
    path = project_dotenv_path()
    _DOTENV_PATH = path
    if not path.is_file():
        _DOTENV_LOADED = False
        return False
    load_dotenv(path, override=False)
    _DOTENV_LOADED = True
    return True


def _var_status(name: str) -> str:
    return "set" if os.getenv(name) else "missing"


def apply_travelport_env_from_mapping(mapping: Any) -> int:
    """
    キー→値のマッピングから Travelport 用環境変数を補完する。
    既に os.environ にあるキーは上書きしない。適用した件数を返す。
    """
    keys = list(REQUIRED_ENV_VARS) + list(OPTIONAL_ENV_VARS)
    applied = 0
    for key in keys:
        if key not in mapping:
            continue
        if os.environ.get(key):
            continue
        value = mapping.get(key) if hasattr(mapping, "get") else mapping[key]
        if value is None or value == "":
            continue
        os.environ[key] = str(value)
        applied += 1
    return applied


def travelport_readiness_report() -> dict[str, Any]:
    """
    Travelport 接続準備の状態を返す（秘密値は含めない）。
    実 API は呼び出さない。
    """
    dotenv_file_present = project_dotenv_path().is_file()
    load_project_dotenv()

    report: dict[str, Any] = {
        "dotenv_path": str(project_dotenv_path()),
        "dotenv_file_present": dotenv_file_present,
        "dotenv_loaded_this_run": _DOTENV_LOADED,
        "required_variables": {name: _var_status(name) for name in REQUIRED_ENV_VARS},
        "optional_variables": {name: _var_status(name) for name in OPTIONAL_ENV_VARS},
        "ready_for_api": False,
        "auth_url": None,
        "search_url": None,
        "auth_header_mode": None,
        "pcc_configured": False,
        "issues": [],
    }

    missing = [k for k, v in report["required_variables"].items() if v == "missing"]
    if missing:
        report["issues"].append(f"必須環境変数が未設定: {', '.join(missing)}")
        return report

    try:
        settings: TravelportSettings = load_travelport_settings()
    except FlightSearchConfigError as exc:
        report["issues"].append(str(exc))
        return report

    report["ready_for_api"] = True
    report["auth_url"] = settings.auth_url
    report["search_url"] = settings.search_url
    report["pcc_configured"] = bool(settings.pcc)
    if settings.access_group:
        report["auth_header_mode"] = "XAUTH_TRAVELPORT_ACCESSGROUP"
    else:
        report["auth_header_mode"] = "TVP-PCC-Core"
    report["gds_suffix"] = settings.gds_suffix
    report["using_default_auth_url"] = settings.auth_url == DEFAULT_AUTH_URL
    report["using_default_api_base"] = settings.api_base_url == DEFAULT_API_BASE_URL
    return report
