"""Manual sanity check for the Duffel integration.

Usage: python scripts/test_duffel.py LHR JFK 2026-10-01 1
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duffel  # noqa: E402


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        return 1
    origin, destination, date, passengers = sys.argv[1:5]
    try:
        offers = duffel.search_offers(origin.upper(), destination.upper(), date, int(passengers))
    except duffel.DuffelError as exc:
        print(f"Duffel error: {exc}")
        return 1

    print(f"{len(offers)} offer(s) returned\n")
    for offer in sorted(offers, key=lambda o: (o["price"] is None, o["price"]))[:5]:
        print(duffel.format_offer(offer))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
