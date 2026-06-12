"""Data classes for cruise fares."""

from dataclasses import dataclass, field, asdict
from typing import Optional
import re


CABIN_RANK: dict[str, int] = {
    # Celebrity Cruises
    "INTERIOR": 0,
    "INSIDE": 0,
    "OCEANVIEW": 1,
    "OCEAN_VIEW": 1,
    "BALCONY": 2,
    "CONCIERGE": 3,
    "AQUA_CLASS": 4,
    "SKY_SUITE": 5,
    "CELEBRITY_SUITE": 6,
    "ROYAL_SUITE": 7,
    "PENTHOUSE_SUITE": 8,
    "REFLECTION_SUITE": 9,
    "THE_RETREAT": 9,
    # Royal Caribbean
    "JUNIOR_SUITE": 5,
    "GRAND_SUITE": 7,
    "OWNERS_SUITE": 8,
    "SKY_LOFT_SUITE": 8,
    "STAR_CLASS": 9,
    # Silversea (all suites ≥ balcony level)
    "SILVER_SUITE": 5,
    "VISTA_SUITE": 2,       # has balcony
    "VERANDA_SUITE": 2,     # has balcony
    "TERRACE_SUITE": 2,     # has private terrace
    "MEDALLION_SUITE": 6,
    "SUPERIOR_VERANDA": 2,
    "GRAND_SILVER_SUITE": 8,
    "OWNERS_SUITE_SS": 9,
    "OTIUM_SUITE": 9,
}


def cabin_rank(name: str) -> int:
    key = re.sub(r"[\s\-]+", "_", name.upper().strip())
    return CABIN_RANK.get(key, -1)


@dataclass
class CruiseFare:
    ship: str
    itinerary: str
    departure_date: str
    duration_nights: int
    cabin_type: str
    price_per_person_eur: float
    total_price_eur: float
    currency: str
    internet_included: bool
    internet_type: Optional[str]   # "premium", "stream", "surf", "basic"
    all_inclusive: bool
    captains_club_eligible: bool
    booking_url: str
    source_url: str = ""
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def id(self) -> str:
        return f"{self.ship}|{self.departure_date}|{self.cabin_type}|{self.price_per_person_eur}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        return d

    def summary(self) -> str:
        internet_note = (
            f"Internet: {self.internet_type.upper()}"
            if self.internet_included and self.internet_type
            else ("Internet: enthalten" if self.internet_included else "Internet: NICHT enthalten")
        )
        ai_note = " | All Inclusive" if self.all_inclusive else ""
        return (
            f"{'=' * 60}\n"
            f"  Schiff    : {self.ship}\n"
            f"  Route     : {self.itinerary}\n"
            f"  Abfahrt   : {self.departure_date}  ({self.duration_nights} Naechte)\n"
            f"  Kabine    : {self.cabin_type}{ai_note}\n"
            f"  Preis     : {self.price_per_person_eur:.0f} EUR/Person  "
            f"(Total: {self.total_price_eur:.0f} EUR)\n"
            f"  {internet_note}\n"
            f"  Captains Club: {'JA' if self.captains_club_eligible else 'NEIN'}\n"
            f"  URL       : {self.booking_url}\n"
            f"{'=' * 60}"
        )
