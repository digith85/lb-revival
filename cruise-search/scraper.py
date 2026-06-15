"""
Multi-line cruise scraper using Playwright.

Covered loyalty programs:
  - Celebrity Cruises  → Captain's Club
  - Royal Caribbean    → Crown & Anchor Society
  - Silversea          → Venetian Society
  (RCL status matching links all three programs)

Strategy: navigate each search page, intercept JSON API responses,
parse CruiseFare objects, filter by configured criteria.
Run with --discover to print all intercepted API URLs for debugging.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Page, Response

from models import CruiseFare

logger = logging.getLogger(__name__)

# Celebrity Cruises Germany search entry point
SEARCH_URL = "https://www.celebritycruises.com/de/cruise-search"
BASE_URL = "https://www.celebritycruises.com/de"

# Cabin type normalisation map (raw API strings → canonical names)
CABIN_NORMALISE: dict[str, str] = {
    "I": "INTERIOR",
    "INSIDE": "INTERIOR",
    "O": "OCEANVIEW",
    "OV": "OCEANVIEW",
    "OCEAN VIEW": "OCEANVIEW",
    "B": "BALCONY",
    "BAL": "BALCONY",
    "BALCONY": "BALCONY",
    "A": "AQUA_CLASS",
    "AQ": "AQUA_CLASS",
    "AQUA CLASS": "AQUA_CLASS",
    "C": "CONCIERGE",
    "CC": "CONCIERGE",
    "SS": "SKY_SUITE",
    "SKY SUITE": "SKY_SUITE",
    "CS": "CELEBRITY_SUITE",
    "CELEBRITY SUITE": "CELEBRITY_SUITE",
    "PS": "PENTHOUSE_SUITE",
    "PENTHOUSE": "PENTHOUSE_SUITE",
    "RS": "REFLECTION_SUITE",
}


def _normalise_cabin(raw: str) -> str:
    key = raw.upper().strip()
    return CABIN_NORMALISE.get(key, key.replace(" ", "_"))


def _parse_price(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        return float(value.get("amount") or value.get("value") or value.get("total") or 0)
    if isinstance(value, str):
        clean = re.sub(r"[^\d.,]", "", value).replace(",", ".")
        try:
            return float(clean)
        except ValueError:
            return 0.0
    return 0.0


def _parse_date(value) -> str:
    """Normalise any date value to YYYY-MM-DD string."""
    if not value:
        return ""
    if isinstance(value, (int, float)) and value > 1_000_000_000:
        try:
            return datetime.fromtimestamp(value / 1000).strftime("%Y-%m-%d")
        except (ValueError, OSError):
            pass
    s = str(value)
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s[: len(fmt)], fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return s


def _internet_from_item(item: dict) -> tuple[bool, Optional[str]]:
    """Detect internet inclusion and quality from a raw API item."""
    blobs = [
        json.dumps(item.get("amenities", "")),
        json.dumps(item.get("packages", "")),
        json.dumps(item.get("inclusions", "")),
        json.dumps(item.get("fareInclusions", "")),
        str(item.get("fareCode", "")),
        str(item.get("packageCode", "")),
        str(item.get("packageType", "")),
    ]
    combined = " ".join(blobs).lower()

    if any(x in combined for x in ("xcelerate", "premium wifi", "premium wi-fi", "premium internet")):
        return True, "premium"
    if any(x in combined for x in ("stream", "streaming wifi", "streaming wi-fi")):
        return True, "stream"
    if any(x in combined for x in ("surf ", "classic wifi", "classic wi-fi", "basic wifi")):
        return True, "surf"
    if any(x in combined for x in ("wifi", "wi-fi", "wlan", "internet")):
        return True, "basic"
    # Celebrity "All Included" fare always includes at least Classic Wi-Fi
    if any(x in combined for x in ("all included", "all-included", "allinclusive", "all inclusive")):
        return True, "surf"
    return False, None


def _all_inclusive_from_item(item: dict) -> bool:
    blob = json.dumps(item).lower()
    return any(x in blob for x in ("all included", "all-included", "allinclusive",
                                    "elevate", "indulge", "retreat", "always included"))


def _captains_club_from_item(item: dict) -> bool:
    brand = str(item.get("brand") or item.get("line") or item.get("companyCode") or "celebrity").lower()
    # All Celebrity sailings earn CC points; exclude explicit non-Celebrity brands
    return "celebrity" in brand or brand in ("x", "")


class CelebrityScraper:
    """Playwright-based scraper for Celebrity Cruises Germany."""

    NUM_PASSENGERS = 3  # 2 adults + 1 infant

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.headless: bool = cfg["scraper"].get("headless", True)
        self.timeout: int = int(cfg["scraper"].get("timeout_seconds", 60)) * 1000
        self.wait_extra: float = float(cfg["scraper"].get("wait_after_load_seconds", 5))
        self.user_agent: str = cfg["scraper"].get("user_agent", "")
        self.log_all: bool = cfg["scraper"].get("log_all_api_calls", False)
        self.executable_path: Optional[str] = cfg["scraper"].get("chromium_executable_path") or self._find_chromium()

    @staticmethod
    def _find_chromium() -> Optional[str]:
        """Auto-detect a usable Chromium binary."""
        import glob as _glob
        import shutil
        for pattern in [
            "/opt/pw-browsers/chromium-*/chrome-linux/chrome",
            "/opt/pw-browsers/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell",
        ]:
            hits = sorted(_glob.glob(pattern), reverse=True)
            if hits:
                logger.debug(f"Auto-detected Chromium: {hits[0]}")
                return hits[0]
        for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
            path = shutil.which(name)
            if path:
                return path
        return None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def fetch_fares(self) -> list[CruiseFare]:
        captured: list[dict] = []

        if not self.executable_path:
            logger.error("Kein Chromium gefunden. Bitte 'playwright install chromium' ausführen.")
            return []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                executable_path=self.executable_path,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                      "--ignore-certificate-errors"],
            )
            ctx = await browser.new_context(
                locale="de-DE",
                user_agent=self.user_agent or None,
                viewport={"width": 1440, "height": 900},
                extra_http_headers={"Accept-Language": "de-DE,de;q=0.9"},
                ignore_https_errors=True,
            )
            page = await ctx.new_page()

            async def on_response(resp: Response) -> None:
                try:
                    url = resp.url
                    ct = resp.headers.get("content-type", "")
                    if "json" not in ct:
                        return
                    if resp.status != 200:
                        return

                    if self.log_all:
                        logger.info(f"[API] {url}")

                    # Only keep responses that look like cruise data
                    if not self._looks_like_cruise_api(url):
                        return

                    body = await resp.json()
                    captured.append({"url": url, "body": body})
                    logger.debug(f"Captured cruise API response: {url}")
                except Exception as exc:
                    logger.debug(f"Response handler error: {exc}")

            page.on("response", on_response)

            try:
                await self._navigate_and_wait(page)
            except Exception as exc:
                logger.error(f"Navigation error: {exc}")
            finally:
                await browser.close()

        fares = self._parse_responses(captured)

        if not fares:
            logger.warning(
                "Keine Tarife aus API-Responses extrahiert. "
                "Starte Celebrity Cruises search mit --discover um API-Endpunkte zu prüfen."
            )

        return fares

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _navigate_and_wait(self, page: Page) -> None:
        logger.info(f"Lade {SEARCH_URL} …")
        await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=self.timeout)

        # Wait for SPA to hydrate and fire initial data requests
        try:
            await page.wait_for_load_state("networkidle", timeout=self.timeout)
        except Exception:
            pass  # networkidle can time out on SPAs; proceed anyway

        await asyncio.sleep(self.wait_extra)

        # Try scrolling to trigger lazy-loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

    @staticmethod
    def _looks_like_cruise_api(url: str) -> bool:
        lower = url.lower()
        keywords = (
            "cruise", "sailing", "itinerary", "adventure", "voyage",
            "fare", "price", "find-a-cruise", "cruisesearch",
        )
        return any(k in lower for k in keywords)

    def _parse_responses(self, responses: list[dict]) -> list[CruiseFare]:
        fares: list[CruiseFare] = []
        seen: set[str] = set()

        for resp in responses:
            url = resp["url"]
            body = resp["body"]
            parsed = self._try_parse(body, url)
            for fare in parsed:
                if fare.id not in seen:
                    seen.add(fare.id)
                    fares.append(fare)

        logger.info(f"{len(fares)} Tarife aus {len(responses)} API-Responses extrahiert")
        return fares

    def _try_parse(self, body, url: str) -> list[CruiseFare]:
        if isinstance(body, list):
            return [f for item in body for f in [self._parse_item(item, url)] if f]

        if isinstance(body, dict):
            for key in ("cruises", "results", "data", "sailings", "items",
                        "adventures", "cruiseList", "voyages", "offers"):
                sub = body.get(key)
                if isinstance(sub, list):
                    return [f for item in sub for f in [self._parse_item(item, url)] if f]
            # Maybe the dict IS a single cruise
            single = self._parse_item(body, url)
            return [single] if single else []

        return []

    def _parse_item(self, item: dict, source_url: str) -> Optional[CruiseFare]:
        if not isinstance(item, dict):
            return None
        try:
            ship = (item.get("shipName") or item.get("ship") or
                    (item.get("ship", {}) or {}).get("name") or "Unbekannt")
            if isinstance(ship, dict):
                ship = ship.get("name") or "Unbekannt"

            itinerary = (item.get("itineraryName") or item.get("name") or
                         item.get("title") or item.get("description") or "Unbekannte Route")

            dep_raw = (item.get("departureDate") or item.get("sailDate") or
                       item.get("embarkDate") or item.get("startDate") or "")
            departure_date = _parse_date(dep_raw)

            nights = int(item.get("nights") or item.get("duration") or
                         item.get("numNights") or item.get("durationNights") or 0)

            # Price — try balcony price first, then generic
            price_raw = (
                item.get("balconyPrice") or item.get("balconyFromPrice") or
                item.get("fromPrice") or item.get("startingPrice") or
                item.get("price") or item.get("lowestPrice") or 0
            )
            price_pp = _parse_price(price_raw)

            cabin_raw = str(
                item.get("cabinType") or item.get("stateroom") or
                item.get("category") or item.get("roomType") or "BALCONY"
            )
            cabin_type = _normalise_cabin(cabin_raw)

            internet_inc, internet_type = _internet_from_item(item)
            all_inc = _all_inclusive_from_item(item)
            cc_eligible = _captains_club_from_item(item)

            currency = str(item.get("currency") or item.get("currencyCode") or "EUR")

            booking_url = (
                item.get("bookingUrl") or item.get("url") or
                item.get("deepLink") or SEARCH_URL
            )

            total = price_pp * self.NUM_PASSENGERS

            return CruiseFare(
                ship=str(ship).strip(),
                itinerary=str(itinerary).strip(),
                departure_date=departure_date,
                duration_nights=nights,
                cabin_type=cabin_type,
                price_per_person_eur=price_pp,
                total_price_eur=total,
                currency=currency,
                internet_included=internet_inc,
                internet_type=internet_type,
                all_inclusive=all_inc,
                captains_club_eligible=cc_eligible,
                booking_url=str(booking_url),
                source_url=source_url,
                raw=item,
            )
        except Exception as exc:
            logger.debug(f"parse_item failed: {exc}")
            return None


# ---------------------------------------------------------------------------
# Royal Caribbean scraper
# ---------------------------------------------------------------------------

class RoyalCaribbeanScraper(CelebrityScraper):
    """
    Scraper for Royal Caribbean Germany.
    Inherits Playwright logic from CelebrityScraper; overrides URL and keywords.
    Loyalty: Crown & Anchor Society (RCL status-match with Captain's Club).
    """

    SEARCH_URL_RC = "https://www.royalcaribbean.com/de/find-a-cruise"

    async def fetch_fares(self) -> list[CruiseFare]:
        captured: list[dict] = []

        if not self.executable_path:
            logger.error("[RC] Kein Chromium gefunden.")
            return []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                executable_path=self.executable_path,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                      "--ignore-certificate-errors"],
            )
            ctx = await browser.new_context(
                locale="de-DE",
                user_agent=self.user_agent or None,
                viewport={"width": 1440, "height": 900},
                extra_http_headers={"Accept-Language": "de-DE,de;q=0.9"},
                ignore_https_errors=True,
            )
            page = await ctx.new_page()

            async def on_response(resp: Response) -> None:
                try:
                    if "json" not in resp.headers.get("content-type", ""):
                        return
                    if resp.status != 200:
                        return
                    url = resp.url
                    if self.log_all:
                        logger.info(f"[RC API] {url}")
                    if not self._looks_like_cruise_api(url):
                        return
                    body = await resp.json()
                    captured.append({"url": url, "body": body})
                    logger.debug(f"[RC] Captured: {url}")
                except Exception as exc:
                    logger.debug(f"[RC] Response error: {exc}")

            page.on("response", on_response)
            try:
                logger.info(f"[Royal Caribbean] Lade {self.SEARCH_URL_RC} …")
                await page.goto(self.SEARCH_URL_RC, wait_until="domcontentloaded", timeout=self.timeout)
                try:
                    await page.wait_for_load_state("networkidle", timeout=self.timeout)
                except Exception:
                    pass
                await asyncio.sleep(self.wait_extra)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
            except Exception as exc:
                logger.error(f"[RC] Navigation error: {exc}")
            finally:
                await browser.close()

        fares = self._parse_responses(captured)
        # Tag all fares with RC loyalty info
        for fare in fares:
            if not fare.captains_club_eligible:
                fare.captains_club_eligible = True  # Crown & Anchor = status-matched
        return fares

    @staticmethod
    def _looks_like_cruise_api(url: str) -> bool:
        lower = url.lower()
        keywords = ("cruise", "sailing", "ship", "voyage", "itinerary", "fare",
                    "price", "offer", "search", "stateroom")
        return any(k in lower for k in keywords)


# ---------------------------------------------------------------------------
# Silversea scraper
# ---------------------------------------------------------------------------

class SilverseaScraper(CelebrityScraper):
    """
    Scraper for Silversea Germany.
    All Silversea cabins are suites (≥ balcony level by default).
    Loyalty: Venetian Society (RCL status-match with Captain's Club).
    """

    SEARCH_URL_SS = "https://www.silversea.com/de/kreuzfahrten.html"

    async def fetch_fares(self) -> list[CruiseFare]:
        captured: list[dict] = []

        if not self.executable_path:
            logger.error("[SS] Kein Chromium gefunden.")
            return []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                executable_path=self.executable_path,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                      "--ignore-certificate-errors"],
            )
            ctx = await browser.new_context(
                locale="de-DE",
                user_agent=self.user_agent or None,
                viewport={"width": 1440, "height": 900},
                extra_http_headers={"Accept-Language": "de-DE,de;q=0.9"},
                ignore_https_errors=True,
            )
            page = await ctx.new_page()

            async def on_response(resp: Response) -> None:
                try:
                    if "json" not in resp.headers.get("content-type", ""):
                        return
                    if resp.status != 200:
                        return
                    url = resp.url
                    if self.log_all:
                        logger.info(f"[SS API] {url}")
                    if not self._looks_like_cruise_api(url):
                        return
                    body = await resp.json()
                    captured.append({"url": url, "body": body})
                    logger.debug(f"[Silversea] Captured: {url}")
                except Exception as exc:
                    logger.debug(f"[SS] Response error: {exc}")

            page.on("response", on_response)
            try:
                logger.info(f"[Silversea] Lade {self.SEARCH_URL_SS} …")
                await page.goto(self.SEARCH_URL_SS, wait_until="domcontentloaded", timeout=self.timeout)
                try:
                    await page.wait_for_load_state("networkidle", timeout=self.timeout)
                except Exception:
                    pass
                await asyncio.sleep(self.wait_extra)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
            except Exception as exc:
                logger.error(f"[SS] Navigation error: {exc}")
            finally:
                await browser.close()

        fares = self._parse_responses(captured)
        # Silversea: all cabins are suites → always meets balcony minimum
        for fare in fares:
            if fare.cabin_type in ("INTERIOR", "OCEANVIEW", "INSIDE", ""):
                fare.cabin_type = "SILVER_SUITE"
            fare.captains_club_eligible = True  # Venetian Society ↔ Captain's Club status match
        return fares

    @staticmethod
    def _looks_like_cruise_api(url: str) -> bool:
        lower = url.lower()
        keywords = ("voyage", "cruise", "sailing", "itinerary", "search",
                    "api", "price", "offer", "expedition")
        return any(k in lower for k in keywords)


# ---------------------------------------------------------------------------
# Aggregator: runs all scrapers and combines results
# ---------------------------------------------------------------------------

async def fetch_all_fares(cfg: dict) -> list[CruiseFare]:
    """Run Celebrity, Royal Caribbean and Silversea scrapers concurrently."""
    lines = cfg.get("cruise_lines", ["celebrity", "royal_caribbean", "silversea"])

    tasks = []
    if "celebrity" in lines:
        tasks.append(CelebrityScraper(cfg).fetch_fares())
    if "royal_caribbean" in lines:
        tasks.append(RoyalCaribbeanScraper(cfg).fetch_fares())
    if "silversea" in lines:
        tasks.append(SilverseaScraper(cfg).fetch_fares())

    results = await asyncio.gather(*tasks, return_exceptions=True)

    fares: list[CruiseFare] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Scraper-Fehler: {result}")
        else:
            fares.extend(result)

    logger.info(f"Gesamt: {len(fares)} Tarife von allen Kreuzfahrtlinien")
    return fares
