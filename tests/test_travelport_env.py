import os
from pathlib import Path

import pytest

from nexttrip.flights.env_loader import load_project_dotenv, travelport_readiness_report


def test_load_project_dotenv_reads_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TRAVELPORT_CLIENT_ID=from_dotenv\n"
        "TRAVELPORT_CLIENT_SECRET=secret\n"
        "TRAVELPORT_USERNAME=user\n"
        "TRAVELPORT_PASSWORD=pass\n"
        "TRAVELPORT_PCC=ABC1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "nexttrip.flights.env_loader.project_dotenv_path",
        lambda: env_file,
    )
    for key in (
        "TRAVELPORT_CLIENT_ID",
        "TRAVELPORT_CLIENT_SECRET",
        "TRAVELPORT_USERNAME",
        "TRAVELPORT_PASSWORD",
        "TRAVELPORT_PCC",
    ):
        monkeypatch.delenv(key, raising=False)

    assert load_project_dotenv() is True
    assert os.environ["TRAVELPORT_CLIENT_ID"] == "from_dotenv"
    assert os.environ["TRAVELPORT_PCC"] == "ABC1"


def test_dotenv_does_not_override_existing_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("TRAVELPORT_CLIENT_ID=from_file\n", encoding="utf-8")
    monkeypatch.setattr(
        "nexttrip.flights.env_loader.project_dotenv_path",
        lambda: env_file,
    )
    monkeypatch.setenv("TRAVELPORT_CLIENT_ID", "from_shell")
    load_project_dotenv()
    assert os.environ["TRAVELPORT_CLIENT_ID"] == "from_shell"


def test_readiness_report_masks_secrets(monkeypatch):
    for key, val in {
        "TRAVELPORT_CLIENT_ID": "id",
        "TRAVELPORT_CLIENT_SECRET": "super-secret-value",
        "TRAVELPORT_USERNAME": "user1",
        "TRAVELPORT_PASSWORD": "pass1",
        "TRAVELPORT_PCC": "ABC1",
    }.items():
        monkeypatch.setenv(key, val)
    report = travelport_readiness_report()
    blob = str(report)
    assert "super-secret-value" not in blob
    assert "pass1" not in blob
    assert report["required_variables"]["TRAVELPORT_CLIENT_SECRET"] == "set"


def test_readiness_report_ready_when_all_set(monkeypatch):
    for key, val in {
        "TRAVELPORT_CLIENT_ID": "id",
        "TRAVELPORT_CLIENT_SECRET": "sec",
        "TRAVELPORT_USERNAME": "u",
        "TRAVELPORT_PASSWORD": "p",
        "TRAVELPORT_PCC": "DU7",
    }.items():
        monkeypatch.setenv(key, val)
    monkeypatch.setattr(
        "nexttrip.flights.env_loader.project_dotenv_path",
        lambda: Path("/nonexistent/.env"),
    )
    report = travelport_readiness_report()
    assert report["ready_for_api"] is True
    assert report["auth_header_mode"] == "TVP-PCC-Core"
    assert "catalog/search/catalogproductofferings" in report["search_url"]
    assert "sec" not in str(report)
