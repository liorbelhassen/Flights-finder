"""Minimal Duffel API client: one-way flight search via offer requests."""
import logging

import requests

import config

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60


class DuffelError(Exception):
    """Raised when the Duffel API cannot be queried or returns an error."""


def search_offers(origin, destination, departure_date, passengers):
    """Create an offer request and return the list of offers.

    Raises DuffelError on missing credentials, network problems, rate limiting
    or any non-2xx response so callers can log and retry later.
    """
    if not config.DUFFEL_API_KEY:
        raise DuffelError("DUFFEL_API_KEY is not set")

    payload = {
        "data": {
            "slices": [
                {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                }
            ],
            "passengers": [{"type": "adult"} for _ in range(passengers)],
        }
    }
    headers = {
        "Authorization": f"Bearer {config.DUFFEL_API_KEY}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    url = f"{config.DUFFEL_API_URL}/air/offer_requests?return_offers=true"
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise DuffelError(f"request to Duffel failed: {exc}") from exc

    if response.status_code == 429:
        raise DuffelError("rate limited by Duffel (HTTP 429)")
    if response.status_code >= 400:
        raise DuffelError(f"Duffel returned HTTP {response.status_code}: {_error_detail(response)}")

    try:
        offers = response.json()["data"]["offers"]
    except (ValueError, KeyError, TypeError) as exc:
        raise DuffelError(f"unexpected Duffel response body: {exc}") from exc

    return [summarize_offer(offer) for offer in offers]


def _error_detail(response):
    try:
        errors = response.json().get("errors") or []
    except ValueError:
        return response.text[:300]
    messages = [f"{e.get('title')}: {e.get('message')}" for e in errors]
    return "; ".join(messages) or response.text[:300]


def summarize_offer(offer):
    """Flatten a Duffel offer into the fields the app stores and emails."""
    segments = [seg for slice_ in offer.get("slices", []) for seg in slice_.get("segments", [])]
    first = segments[0] if segments else {}
    last = segments[-1] if segments else {}
    carrier = (offer.get("owner") or first.get("marketing_carrier") or {}).get("name", "Unknown airline")

    try:
        price = float(offer.get("total_amount"))
    except (TypeError, ValueError):
        price = None

    return {
        "id": offer.get("id"),
        "airline": carrier,
        "price": price,
        "currency": offer.get("total_currency", ""),
        "departing_at": first.get("departing_at", ""),
        "arriving_at": last.get("arriving_at", ""),
        "origin": (first.get("origin") or {}).get("iata_code", ""),
        "destination": (last.get("destination") or {}).get("iata_code", ""),
        "stops": max(len(segments) - 1, 0),
        "flight_numbers": ", ".join(
            f"{(seg.get('marketing_carrier') or {}).get('iata_code', '')}{seg.get('marketing_carrier_flight_number', '')}"
            for seg in segments
        ),
    }


def format_offer(offer):
    price = "unknown price" if offer["price"] is None else f"{offer['price']:.2f} {offer['currency']}"
    stops = "direct" if offer["stops"] == 0 else f"{offer['stops']} stop(s)"
    return (
        f"{offer['airline']} ({offer['flight_numbers']}) — {price}\n"
        f"  {offer['origin']} {offer['departing_at']} -> {offer['destination']} {offer['arriving_at']} ({stops})\n"
        f"  offer id: {offer['id']}"
    )
