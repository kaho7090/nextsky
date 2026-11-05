from nexttrip.flights.ui import target_country_context, target_country_label


def _country(**overrides):
    base = {
        "code": "ML",
        "name_en": "Mali",
        "name_ja": "マリ",
        "visited": 0,
        "priority": 0,
        "risk_level": None,
        "risk_trend": "",
        "risk_note": "",
        "in_risk_watch": 0,
    }
    base.update(overrides)
    return base


def test_target_country_label_format():
    assert target_country_label(_country()) == "マリ (Mali) [ML]"


def test_context_empty_for_non_watch_country():
    assert target_country_context(_country()) == ""


def test_context_includes_level_trend_and_note():
    country = _country(
        in_risk_watch=1,
        risk_level=5,
        risk_trend="up",
        risk_note="枠組みで唯一のLv.5",
    )
    context = target_country_context(country)
    assert "リスクLv.5" in context
    assert "↑" in context
    assert "枠組みで唯一のLv.5" in context


def test_context_trend_only_when_level_unrated():
    country = _country(in_risk_watch=1, risk_level=None, risk_trend="down")
    context = target_country_context(country)
    assert "リスクLv" not in context
    assert "↓" in context
