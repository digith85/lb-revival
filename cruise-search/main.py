#!/usr/bin/env python3
"""
Cruise Fare Monitor
===================
Sucht kontinuierlich nach günstigen Kreuzfahrttarifen bei:
  - Celebrity Cruises   (Captain's Club)
  - Royal Caribbean     (Crown & Anchor Society)
  - Silversea           (Venetian Society)

Filterkriterien:
  a) Balkon-Kabine oder höher
  b) Schnelles Internet (Stream / Premium) verfügbar / enthalten
  c) 2 Erwachsene + 1 Kind (geb. 25.10.2025)

Verwendung:
  python main.py                   # Einmaliger Lauf + dann Daemon (lt. config)
  python main.py --once            # Nur einmal suchen
  python main.py --discover        # Alle API-Calls loggen (zum Debuggen)
  python main.py --config my.json  # Andere Konfigurationsdatei

Konfiguration: config.json
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import schedule
import time

from filters import FareFilter
from models import CruiseFare
from notifier import Notifier
from scraper import fetch_all_fares

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("cruise_search.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core search function
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    cfg_path = Path(path)
    if not cfg_path.exists():
        logger.error(f"Konfigurationsdatei nicht gefunden: {path}")
        sys.exit(1)
    with open(cfg_path, encoding="utf-8") as fh:
        raw = fh.read()
    # Strip JSON comments (lines starting with //)
    lines = [l for l in raw.splitlines() if not l.strip().startswith("//")]
    return json.loads("\n".join(lines))


async def run_search(cfg: dict, discover: bool = False) -> list[CruiseFare]:
    """One full search cycle: scrape → filter → notify."""
    if discover:
        cfg = dict(cfg)
        cfg["scraper"] = dict(cfg.get("scraper", {}))
        cfg["scraper"]["log_all_api_calls"] = True

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    logger.info(f"=== Suchlauf gestartet: {ts} ===")

    fares = await fetch_all_fares(cfg)

    if not fares:
        logger.info("Keine Tarife von den Scrapern erhalten. Möglicherweise API-Änderung.")
        return []

    logger.info(f"Gesamt rohe Tarife: {len(fares)}")

    fare_filter = FareFilter(cfg)
    matched: list[CruiseFare] = []
    for fare in fares:
        ok, reasons = fare_filter.passes(fare)
        if ok:
            matched.append(fare)
        else:
            logger.debug(f"Abgelehnt ({fare.ship} {fare.departure_date}): {'; '.join(reasons)}")

    logger.info(f"Passende Tarife nach Filter: {len(matched)}")

    notifier = Notifier(cfg)
    notifier.notify(matched, context=f"Suchlauf {ts}")

    return matched


def run_search_sync(cfg: dict, discover: bool = False) -> None:
    asyncio.run(run_search(cfg, discover=discover))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cruise Fare Monitor — Celebrity · Royal Caribbean · Silversea",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config", default="config.json",
        help="Pfad zur Konfigurationsdatei (default: config.json)"
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Nur einmal suchen, dann beenden"
    )
    parser.add_argument(
        "--discover", action="store_true",
        help="Alle intercepted API-Calls loggen (nützlich zum Debuggen)"
    )
    parser.add_argument(
        "--interval", type=int, default=0,
        help="Suchintervall in Minuten (überschreibt config.json)"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Debug-Logging aktivieren"
    )
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    cfg = load_config(args.config)

    if args.discover:
        cfg["scraper"]["log_all_api_calls"] = True

    interval = args.interval or cfg.get("schedule", {}).get("interval_minutes", 60)
    run_on_start = cfg.get("schedule", {}).get("run_on_start", True)

    if args.once:
        run_search_sync(cfg, discover=args.discover)
        return

    logger.info(
        f"Cruise Fare Monitor gestartet.\n"
        f"  Linien  : {cfg.get('cruise_lines', ['celebrity', 'royal_caribbean', 'silversea'])}\n"
        f"  Intervall: alle {interval} Minuten\n"
        f"  Filter  : Balkon+, Schnelles Internet, 2 Erw. + Kind (geb. "
        f"{cfg['passengers']['children'][0]['dob']})\n"
        f"  Logs    : cruise_search.log\n"
        f"  Ergebnisse: {cfg['notification']['results_file']}\n"
        f"  Ctrl+C zum Beenden."
    )

    if run_on_start:
        run_search_sync(cfg, discover=args.discover)

    schedule.every(interval).minutes.do(run_search_sync, cfg=cfg, discover=args.discover)

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Monitor beendet.")


if __name__ == "__main__":
    main()
