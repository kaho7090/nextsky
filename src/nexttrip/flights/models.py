from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class FlightSearchParams:
    origin: str
    destination: str
    departure_date: date
    adults: int = 1


@dataclass
class TaxLine:
    code: str
    amount: float | None


@dataclass
class FlightOffer:
    offer_id: str
    carrier: str | None
    flight_numbers: list[str]
    origin: str | None
    destination: str | None
    departure_time: str | None
    arrival_time: str | None
    stops: int | None
    currency: str | None
    base_fare: float | None
    total_taxes: float | None
    total_price: float | None
    tax_breakdown: list[TaxLine] = field(default_factory=list)
    surcharge_lines: list[TaxLine] = field(default_factory=list)
    fare_basis_codes: list[str] = field(default_factory=list)
    fare_calculation: str | None = None
    fare_calculation_available: bool = False
