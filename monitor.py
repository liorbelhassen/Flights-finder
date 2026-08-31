"""One check cycle: search Duffel, detect new/better offers, email once each."""
import logging

import config
import db
import duffel
import mailer

logger = logging.getLogger(__name__)

MAX_OFFERS_PER_EMAIL = 10


def check_once():
    """Run a single check. Never raises: failures are logged to the checks table."""
    search = db.get_search()
    if not search:
        logger.info("No saved search, skipping check")
        return {"status": "skipped", "detail": "no saved search"}

    try:
        offers = duffel.search_offers(
            search["origin"],
            search["destination"],
            search["departure_date"],
            search["passengers"],
        )
    except duffel.DuffelError as exc:
        logger.warning("Duffel check failed: %s", exc)
        db.log_check("error", str(exc))
        return {"status": "error", "detail": str(exc)}

    matching = [o for o in offers if _matches(o, search["max_price"])]
    new_offers = _new_or_better(matching)

    if not new_offers:
        detail = f"{len(matching)} matching offer(s), nothing new"
        db.log_check("ok", detail, offers_found=len(matching))
        return {"status": "ok", "detail": detail, "offers_found": len(matching)}

    try:
        _send_alert(search, new_offers)
    except mailer.MailError as exc:
        # Do not record the offers, so the alert is retried on the next cycle.
        logger.warning("Alert email failed: %s", exc)
        db.log_check("error", f"found {len(new_offers)} new offer(s) but email failed: {exc}",
                     offers_found=len(matching))
        return {"status": "error", "detail": str(exc), "offers_found": len(matching)}

    for offer in new_offers:
        db.record_offer(offer["signature"], offer["id"], offer["price"])

    detail = f"{len(matching)} matching offer(s), emailed {len(new_offers)} new/better offer(s)"
    db.log_check("alerted", detail, offers_found=len(matching), alerts_sent=len(new_offers))
    return {"status": "alerted", "detail": detail, "offers_found": len(matching)}


def _matches(offer, max_price):
    if offer["id"] is None:
        return False
    if max_price is None:
        return True
    return offer["price"] is not None and offer["price"] <= max_price


def _new_or_better(offers):
    """Offers whose itinerary has not been reported yet, or is now clearly cheaper.

    Keyed on the itinerary signature, not the Duffel offer id: Duffel returns a
    fresh offer id for every offer request, so ids would never match. Airline
    prices also jitter by small amounts between requests, so a re-alert needs a
    drop of at least MIN_PRICE_DROP_PERCENT against the best price reported so far.
    """
    seen = db.seen_offers()
    cheapest = {}
    for offer in offers:
        signature = offer["signature"]
        current = cheapest.get(signature)
        if current is None or _is_cheaper(offer["price"], current["price"]):
            cheapest[signature] = offer

    result = []
    for signature, offer in cheapest.items():
        if signature not in seen:
            result.append(offer)
            continue
        if _is_significant_drop(offer["price"], seen[signature]):
            result.append(offer)
    return result


def _is_cheaper(price, reference):
    return price is not None and reference is not None and price < reference


def _is_significant_drop(price, reference):
    if price is None or reference is None:
        return False
    return price <= reference * (1 - config.MIN_PRICE_DROP_PERCENT / 100)


def _send_alert(search, offers):
    offers = sorted(offers, key=lambda o: (o["price"] is None, o["price"]))
    route = f"{search['origin']}->{search['destination']} on {search['departure_date']}"
    cheapest = offers[0]
    price = "unknown price" if cheapest["price"] is None else f"{cheapest['price']:.2f} {cheapest['currency']}"

    lines = [
        f"New flight availability for {route} ({search['passengers']} passenger(s)).",
        "",
    ]
    for offer in offers[:MAX_OFFERS_PER_EMAIL]:
        lines.append(duffel.format_offer(offer))
        lines.append("")
    if len(offers) > MAX_OFFERS_PER_EMAIL:
        lines.append(f"...and {len(offers) - MAX_OFFERS_PER_EMAIL} more offer(s).")

    mailer.send_email(
        search["email"],
        f"Flight alert: {route} from {price}",
        "\n".join(lines),
    )
