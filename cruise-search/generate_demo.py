#!/usr/bin/env python3
"""Generates a demo found_fares.json with realistic sample data."""

import json
from datetime import datetime

sample_fares = [
    {
        "id": "Celebrity Apex|2026-07-12|BALCONY|1189.0",
        "found_at": datetime.now().isoformat(),
        "ship": "Celebrity Apex",
        "itinerary": "Westliches Mittelmeer ab Barcelona",
        "departure_date": "2026-07-12",
        "duration_nights": 7,
        "cabin_type": "BALCONY",
        "price_per_person_eur": 1189.0,
        "total_price_eur": 3567.0,
        "price_per_night_eur": 509.57,
        "currency": "EUR",
        "internet_included": True,
        "internet_type": "stream",
        "all_inclusive": True,
        "captains_club_eligible": True,
        "booking_url": "https://www.celebritycruises.com/de/cruise-search",
        "source_url": "https://www.celebritycruises.com/de/cruise-search"
    },
    {
        "id": "Celebrity Beyond|2026-09-03|AQUA_CLASS|1549.0",
        "found_at": datetime.now().isoformat(),
        "ship": "Celebrity Beyond",
        "itinerary": "Griechische Inseln ab Athen",
        "departure_date": "2026-09-03",
        "duration_nights": 10,
        "cabin_type": "AQUA_CLASS",
        "price_per_person_eur": 1549.0,
        "total_price_eur": 4647.0,
        "price_per_night_eur": 464.70,
        "currency": "EUR",
        "internet_included": True,
        "internet_type": "premium",
        "all_inclusive": True,
        "captains_club_eligible": True,
        "booking_url": "https://www.celebritycruises.com/de/cruise-search",
        "source_url": "https://www.celebritycruises.com/de/cruise-search"
    },
    {
        "id": "Wonder of the Seas|2026-08-22|BALCONY|1099.0",
        "found_at": datetime.now().isoformat(),
        "ship": "Wonder of the Seas",
        "itinerary": "Mittelmeer ab Barcelona",
        "departure_date": "2026-08-22",
        "duration_nights": 7,
        "cabin_type": "BALCONY",
        "price_per_person_eur": 1099.0,
        "total_price_eur": 3297.0,
        "price_per_night_eur": 471.00,
        "currency": "EUR",
        "internet_included": True,
        "internet_type": "stream",
        "all_inclusive": False,
        "captains_club_eligible": True,
        "booking_url": "https://www.royalcaribbean.com/de/",
        "source_url": "https://www.royalcaribbean.com/de/"
    },
    {
        "id": "Silver Nova|2026-10-10|VERANDA_SUITE|3290.0",
        "found_at": datetime.now().isoformat(),
        "ship": "Silver Nova",
        "itinerary": "Kanarische Inseln & Marokko",
        "departure_date": "2026-10-10",
        "duration_nights": 10,
        "cabin_type": "VERANDA_SUITE",
        "price_per_person_eur": 3290.0,
        "total_price_eur": 9870.0,
        "price_per_night_eur": 987.00,
        "currency": "EUR",
        "internet_included": True,
        "internet_type": "premium",
        "all_inclusive": True,
        "captains_club_eligible": True,
        "booking_url": "https://www.silversea.com/de/",
        "source_url": "https://www.silversea.com/de/"
    }
]

with open("found_fares.json", "w", encoding="utf-8") as f:
    json.dump(sample_fares, f, ensure_ascii=False, indent=2)

print(f"Demo-Datei erstellt: found_fares.json ({len(sample_fares)} Tarife)")
print()
print("Vorschau:")
print()
for fare in sample_fares:
    ai = " | All Inclusive" if fare["all_inclusive"] else ""
    print(f"  {fare['ship']} | {fare['itinerary']}")
    print(f"  {fare['departure_date']} | {fare['duration_nights']} Nächte | {fare['cabin_type']}{ai}")
    print(f"  {fare['price_per_person_eur']:.0f} EUR/Person | Total: {fare['total_price_eur']:.0f} EUR | {fare['price_per_night_eur']:.0f} EUR/Nacht")
    print(f"  Internet: {fare['internet_type'].upper()} | Captain's Club: {'JA' if fare['captains_club_eligible'] else 'NEIN'}")
    print()
