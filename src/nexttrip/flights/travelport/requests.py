from __future__ import annotations

from nexttrip.flights.config import TravelportSettings
from nexttrip.flights.models import FlightSearchParams


def build_catalog_search_payload(
    params: FlightSearchParams,
    settings: TravelportSettings,
) -> dict:
    """Flights Search API（CatalogProductOfferings）のリクエスト JSON。"""
    return {
        "@type": "CatalogProductOfferingsQueryRequest",
        "CatalogProductOfferingsRequest": {
            "@type": "CatalogProductOfferingsRequestAir",
            "contentSourceList": ["GDS"],
            "offersPerPage": 10,
            "maxNumberOfUpsellsToReturn": 0,
            "PassengerCriteria": [
                {
                    "@type": "PassengerCriteria",
                    "number": params.adults,
                    "passengerTypeCode": "ADT",
                }
            ],
            "SearchCriteriaFlight": [
                {
                    "@type": "SearchCriteriaFlight",
                    "departureDate": params.departure_date.isoformat(),
                    "From": {"value": params.origin.upper()},
                    "To": {"value": params.destination.upper()},
                }
            ],
            "PricingModifiersAir": {
                "@type": "PricingModifiersAir",
                "PricingPCC": settings.pcc,
            },
            "CustomResponseModifiersAir": {
                "@type": "CustomResponseModifiersAir",
                "SearchRepresentation": "Journey",
                "includeFareCalculationInd": True,
            },
        },
    }


def build_search_headers(token: str, settings: TravelportSettings) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Version": "11",
        "Content-Version": "11",
    }
    if settings.access_group:
        headers["XAUTH_TRAVELPORT_ACCESSGROUP"] = settings.access_group
    else:
        headers["TVP-PCC-Core"] = settings.tvp_pcc_core
    return headers
