"""Notification channels: console, email, JSON file."""

import json
import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from models import CruiseFare

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.console: bool = cfg["notification"].get("console", True)
        self.results_file: str = cfg["notification"].get("results_file", "found_fares.json")
        self.email_cfg: dict = cfg["notification"].get("email", {})

    def notify(self, fares: list[CruiseFare], context: str = "") -> None:
        if not fares:
            logger.info(f"[{context or 'Suche'}] Keine passenden Tarife gefunden.")
            return

        logger.info(f"[{context or 'Suche'}] {len(fares)} Tarif(e) gefunden!")

        if self.console:
            self._print_fares(fares, context)

        self._save_to_file(fares)

        if self.email_cfg.get("enabled"):
            self._send_email(fares, context)

    # ------------------------------------------------------------------

    def _print_fares(self, fares: list[CruiseFare], context: str) -> None:
        print(f"\n{'#' * 60}")
        print(f"  {len(fares)} PASSENDE TARIFE — {context or datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'#' * 60}\n")
        for fare in fares:
            print(fare.summary())
        print()

    def _save_to_file(self, fares: list[CruiseFare]) -> None:
        path = Path(self.results_file)
        existing: list[dict] = []
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                existing = []

        existing_ids = {e.get("id") for e in existing}
        new_entries = [
            {"id": f.id, "found_at": datetime.now().isoformat(), **f.to_dict()}
            for f in fares
            if f.id not in existing_ids
        ]

        if new_entries:
            existing.extend(new_entries)
            path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"{len(new_entries)} neue Tarife in '{path}' gespeichert.")

    def _send_email(self, fares: list[CruiseFare], context: str) -> None:
        try:
            cfg = self.email_cfg
            subject = f"[Cruise Finder] {len(fares)} passende Tarife – {context or datetime.now().strftime('%Y-%m-%d')}"

            text_body = f"Es wurden {len(fares)} passende Kreuzfahrt-Tarife gefunden:\n\n"
            html_rows = ""
            for fare in fares:
                text_body += fare.summary() + "\n\n"
                html_rows += f"""
                <tr>
                  <td>{fare.ship}</td>
                  <td>{fare.itinerary}</td>
                  <td>{fare.departure_date}</td>
                  <td>{fare.duration_nights} N</td>
                  <td>{fare.cabin_type}</td>
                  <td><b>{fare.price_per_person_eur:.0f} EUR</b></td>
                  <td>{'✓ ' + (fare.internet_type or '') if fare.internet_included else '✗'}</td>
                  <td>{'✓' if fare.all_inclusive else ''}</td>
                  <td><a href="{fare.booking_url}">Buchen</a></td>
                </tr>"""

            html_body = f"""<html><body>
            <h2>{len(fares)} passende Kreuzfahrt-Tarife</h2>
            <p>Alle Tarife erfüllen: Balkon oder höher · Schnelles Internet · 2 Erw. + Kind · Captain's Club</p>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse">
              <tr style="background:#003087;color:white">
                <th>Schiff</th><th>Route</th><th>Abfahrt</th><th>Nächte</th>
                <th>Kabine</th><th>Preis/P.</th><th>Internet</th><th>AI</th><th>Link</th>
              </tr>
              {html_rows}
            </table>
            <p style="font-size:0.8em;color:gray">Generiert: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            </body></html>"""

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = cfg["from"]
            msg["To"] = cfg["to"]
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            ctx = ssl.create_default_context()
            with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as smtp:
                smtp.ehlo()
                if cfg.get("use_tls", True):
                    smtp.starttls(context=ctx)
                smtp.login(cfg["username"], cfg["password"])
                smtp.sendmail(cfg["from"], cfg["to"], msg.as_string())

            logger.info(f"E-Mail gesendet an {cfg['to']}")
        except Exception as exc:
            logger.error(f"E-Mail fehlgeschlagen: {exc}")
