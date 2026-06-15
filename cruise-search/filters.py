"""Filtering logic for cruise fares based on search criteria."""

import logging
from datetime import date, datetime
from typing import Optional

from models import CruiseFare, cabin_rank

logger = logging.getLogger(__name__)


class FareFilter:
    """Applies all configured criteria to a CruiseFare and returns whether it passes."""

    MIN_INFANT_AGE_MONTHS_STANDARD = 6
    MIN_INFANT_AGE_MONTHS_TRANSATLANTIC = 12

    TRANSATLANTIC_KEYWORDS = [
        "transatlantik", "transatlantic", "repositioning", "umpositionierung"
    ]

    def __init__(self, config: dict):
        self.cfg = config
        self.child_dob = self._parse_date(config["passengers"]["children"][0]["dob"])
        self.min_cabin_rank = cabin_rank(config["cabin"]["min_category"])
        self.require_fast_internet = config["internet"]["require_fast"]
        self.accept_upgradeable = config["internet"].get("accept_upgradeable", True)
        self.departure_from = self._parse_date(config["search"]["departure_date_from"])
        self.departure_to = self._parse_date(config["search"]["departure_date_to"])
        self.min_nights = config["search"].get("min_duration_nights", 0)
        self.max_nights = config["search"].get("max_duration_nights", 999)
        self.max_total = float(config["budget"].get("max_total_eur", 0))

    def passes(self, fare: CruiseFare) -> tuple[bool, list[str]]:
        """Returns (passes: bool, reasons_for_rejection: list[str])"""
        rejections: list[str] = []

        # --- Cabin category ---
        fare_rank = cabin_rank(fare.cabin_type)
        if fare_rank < self.min_cabin_rank:
            rejections.append(
                f"Kabine '{fare.cabin_type}' unter Minimum (rank {fare_rank} < {self.min_cabin_rank})"
            )

        # --- Internet ---
        if self.require_fast_internet:
            if not fare.internet_included:
                rejections.append("Kein Internet enthalten")
            elif fare.internet_type in ("surf", "basic", None):
                rejections.append(
                    f"Internet zu langsam: '{fare.internet_type}' (benötigt: stream/premium)"
                )

        # --- Departure date ---
        dep = self._parse_date(fare.departure_date)
        if dep:
            if self.departure_from and dep < self.departure_from:
                rejections.append(f"Abfahrt {fare.departure_date} vor {self.departure_from}")
            if self.departure_to and dep > self.departure_to:
                rejections.append(f"Abfahrt {fare.departure_date} nach {self.departure_to}")
            child_age_months = self._months_between(self.child_dob, dep)
            is_transatlantic = any(
                k in fare.itinerary.lower() for k in self.TRANSATLANTIC_KEYWORDS
            )
            required_months = (
                self.MIN_INFANT_AGE_MONTHS_TRANSATLANTIC
                if is_transatlantic
                else self.MIN_INFANT_AGE_MONTHS_STANDARD
            )
            if child_age_months < required_months:
                rejections.append(
                    f"Kind zu jung: {child_age_months:.1f} Monate (mind. {required_months} benötigt)"
                )

        # --- Duration (skip check if duration unknown) ---
        if fare.duration_nights > 0:
            if fare.duration_nights < self.min_nights:
                rejections.append(f"Zu kurz: {fare.duration_nights} Nächte (min {self.min_nights})")
            if fare.duration_nights > self.max_nights:
                rejections.append(f"Zu lang: {fare.duration_nights} Nächte (max {self.max_nights})")

        # --- Budget ---
        if self.max_total > 0 and fare.total_price_eur > self.max_total:
            rejections.append(
                f"Zu teuer: {fare.total_price_eur:.0f} EUR > {self.max_total:.0f} EUR"
            )

        # --- Captain's Club ---
        if not fare.captains_club_eligible:
            rejections.append("Nicht Captain's Club eligible")

        return (len(rejections) == 0, rejections)

    def is_near_miss(self, fare: CruiseFare, rejections: list[str]) -> bool:
        """True if the only rejection reason is slow internet (upgradeable on the ship)."""
        if not self.accept_upgradeable:
            return False
        internet_only = all("Internet zu langsam" in r for r in rejections)
        return len(rejections) == 1 and internet_only and fare.internet_included

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
        return None

    @staticmethod
    def _months_between(start: Optional[date], end: Optional[date]) -> float:
        if not start or not end:
            return 999.0
        return (end.year - start.year) * 12 + (end.month - start.month) + (end.day - start.day) / 30
