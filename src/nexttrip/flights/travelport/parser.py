from __future__ import annotations

from typing import Any

from nexttrip.flights.models import FlightOffer, TaxLine


def _index_reference_lists(response: dict[str, Any]) -> tuple[dict[str, dict], dict[str, dict]]:
    flights: dict[str, dict] = {}
    products: dict[str, dict] = {}
    ref_lists = response.get("ReferenceList") or []
    if isinstance(ref_lists, dict):
        ref_lists = [ref_lists]
    for ref in ref_lists:
        if not isinstance(ref, dict):
            continue
        ref_type = ref.get("@type", "")
        if ref_type == "ReferenceListFlight":
            for flight in ref.get("Flight") or []:
                if isinstance(flight, dict) and flight.get("id"):
                    flights[str(flight["id"])] = flight
        if ref_type == "ReferenceListProduct":
            for product in ref.get("Product") or []:
                if isinstance(product, dict) and product.get("id"):
                    products[str(product["id"])] = product
    return flights, products


def _decimal_amount(value: Any, decimal_place: int | None) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if decimal_place is not None:
        return num / (10 ** int(decimal_place))
    return num


def _extract_price_bundle(price_obj: dict[str, Any] | None) -> dict[str, Any]:
    if not price_obj:
        return {}
    currency_obj = price_obj.get("CurrencyCode") or {}
    decimal_place = currency_obj.get("decimalPlace")
    currency = currency_obj.get("value")
    breakdown = price_obj.get("PriceBreakdown") or []
    fare_calc = None
    fare_basis: list[str] = []
    tax_lines: list[TaxLine] = []
    surcharges: list[TaxLine] = []
    if breakdown and isinstance(breakdown[0], dict):
        bd = breakdown[0]
        fare_calc = bd.get("FareCalculation")
        amount = bd.get("Amount") or {}
        taxes = amount.get("Taxes") or {}
        for tax in taxes.get("Tax") or []:
            if not isinstance(tax, dict):
                continue
            code = str(tax.get("taxCode", ""))
            val = _decimal_amount(tax.get("value"), decimal_place)
            line = TaxLine(code=code, amount=val)
            tax_lines.append(line)
            if code in {"YQ", "YR"}:
                surcharges.append(line)
    return {
        "currency": currency,
        "decimal_place": decimal_place,
        "base": _decimal_amount(price_obj.get("Base"), decimal_place),
        "total_taxes": _decimal_amount(price_obj.get("TotalTaxes"), decimal_place),
        "total_price": _decimal_amount(price_obj.get("TotalPrice"), decimal_place),
        "fare_calculation": fare_calc,
        "tax_lines": tax_lines,
        "surcharges": surcharges,
        "fare_basis": fare_basis,
    }


def _collect_fare_basis(product_refs: list[str], products: dict[str, dict]) -> list[str]:
    codes: list[str] = []
    for pref in product_refs:
        product = products.get(pref)
        if not product:
            continue
        for pf in product.get("PassengerFlight") or []:
            if not isinstance(pf, dict):
                continue
            for fp in pf.get("FlightProduct") or []:
                if not isinstance(fp, dict):
                    continue
                code = fp.get("fareBasisCode")
                if code:
                    codes.append(str(code))
    return codes


def _flight_times(flight_refs: list[str], flights: dict[str, dict]) -> tuple[str | None, str | None, list[str]]:
    dep_times: list[str] = []
    arr_times: list[str] = []
    numbers: list[str] = []
    carriers: list[str] = []
    for ref in flight_refs:
        flight = flights.get(ref)
        if not flight:
            continue
        dep = flight.get("Departure") or {}
        arr = flight.get("Arrival") or {}
        if isinstance(dep, dict) and dep.get("time"):
            dep_times.append(str(dep.get("time")))
        if isinstance(arr, dict) and arr.get("time"):
            arr_times.append(str(arr.get("time")))
        carrier = flight.get("carrier")
        number = flight.get("number")
        if carrier and number:
            numbers.append(f"{carrier}{number}")
        elif carrier:
            numbers.append(str(carrier))
    return (
        dep_times[0] if dep_times else None,
        arr_times[-1] if arr_times else None,
        numbers,
    )


def parse_search_response(payload: dict[str, Any]) -> list[FlightOffer]:
    response = payload.get("CatalogProductOfferingsResponse") or payload
    if not isinstance(response, dict):
        return []
    offerings_root = response.get("CatalogProductOfferings") or {}
    offerings = offerings_root.get("CatalogProductOffering") or []
    if not isinstance(offerings, list):
        offerings = [offerings]

    flights, products = _index_reference_lists(response)
    results: list[FlightOffer] = []

    for offering in offerings:
        if not isinstance(offering, dict):
            continue
        offer_id = str(offering.get("id", ""))
        origin = offering.get("Departure")
        destination = offering.get("Arrival")
        brand_options = offering.get("ProductBrandOptions") or []
        if not brand_options:
            continue
        first_option = brand_options[0] if isinstance(brand_options, list) else brand_options
        if not isinstance(first_option, dict):
            continue
        flight_refs = [str(x) for x in first_option.get("flightRefs") or []]
        dep_time, arr_time, flight_numbers = _flight_times(flight_refs, flights)
        carrier = flight_numbers[0][:2] if flight_numbers else None

        pbo_list = first_option.get("ProductBrandOffering") or []
        if not isinstance(pbo_list, list) or not pbo_list:
            continue
        pbo = pbo_list[0]
        price_obj = pbo.get("BestCombinablePrice") or pbo.get("Price")
        price = _extract_price_bundle(price_obj if isinstance(price_obj, dict) else None)

        product_refs: list[str] = []
        for prod in pbo.get("Product") or []:
            if isinstance(prod, dict) and prod.get("productRef"):
                product_refs.append(str(prod["productRef"]))
        fare_basis = _collect_fare_basis(product_refs, products)

        stops = max(len(flight_refs) - 1, 0) if flight_refs else None
        fare_calc = price.get("fare_calculation")
        results.append(
            FlightOffer(
                offer_id=offer_id or f"offer-{len(results)+1}",
                carrier=carrier,
                flight_numbers=flight_numbers,
                origin=str(origin) if origin else None,
                destination=str(destination) if destination else None,
                departure_time=dep_time,
                arrival_time=arr_time,
                stops=stops,
                currency=price.get("currency"),
                base_fare=price.get("base"),
                total_taxes=price.get("total_taxes"),
                total_price=price.get("total_price"),
                tax_breakdown=price.get("tax_lines") or [],
                surcharge_lines=price.get("surcharges") or [],
                fare_basis_codes=fare_basis,
                fare_calculation=fare_calc,
                fare_calculation_available=bool(fare_calc),
            )
        )
    return results
