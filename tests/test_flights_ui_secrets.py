import os
from unittest.mock import MagicMock, patch

import pytest

from nexttrip.flights.env_loader import apply_travelport_env_from_mapping
from streamlit.errors import StreamlitSecretNotFoundError


def test_apply_travelport_env_from_mapping_does_not_override(monkeypatch):
    monkeypatch.setenv("TRAVELPORT_CLIENT_ID", "existing")
    mapping = {
        "TRAVELPORT_CLIENT_ID": "from_secrets",
        "TRAVELPORT_PCC": "ABC1",
    }
    n = apply_travelport_env_from_mapping(mapping)
    assert os.environ["TRAVELPORT_CLIENT_ID"] == "existing"
    assert os.environ["TRAVELPORT_PCC"] == "ABC1"
    assert n == 1


def test_hydrate_ignores_missing_secrets_file(monkeypatch):
    pytest.importorskip("streamlit")
    from nexttrip.flights.ui import _hydrate_travelport_env_from_streamlit_secrets

    mock_st = MagicMock()
    type(mock_st).secrets = property(
        lambda self: (_ for _ in ()).throw(StreamlitSecretNotFoundError())
    )

    with patch("nexttrip.flights.ui.st", mock_st):
        _hydrate_travelport_env_from_streamlit_secrets()


def test_hydrate_ignores_key_lookup_when_secrets_unavailable(monkeypatch):
    from nexttrip.flights.ui import _hydrate_travelport_env_from_streamlit_secrets

    class SecretsProxy:
        def __contains__(self, key: str) -> bool:
            raise StreamlitSecretNotFoundError("No secrets found.")

    mock_st = MagicMock()
    mock_st.secrets = SecretsProxy()

    with patch("nexttrip.flights.ui.st", mock_st):
        _hydrate_travelport_env_from_streamlit_secrets()
