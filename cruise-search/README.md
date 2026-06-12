# Cruise Fare Monitor

Sucht kontinuierlich nach günstigen Kreuzfahrttarifen bei drei RCL-Marken.

## Abgedeckte Kreuzfahrtlinien

| Linie | Treueprogramm | Status |
|-------|---------------|--------|
| Celebrity Cruises | **Captain's Club** | ✓ |
| Royal Caribbean | Crown & Anchor Society | ✓ Status-Match mit Captain's Club |
| Silversea | Venetian Society | ✓ Status-Match mit Captain's Club |

## Filterkriterien

- **Kabine**: Balkon oder höher (Aqua Class, Sky Suite, Celebrity Suite, etc.)
- **Internet**: Schnelles Internet (Stream / Premium) — *kein* Basic/Surf
- **Passagiere**: 2 Erwachsene + 1 Kind (geb. 25.10.2025)
  - Mindestabfahrt: 25.04.2026 (Kind mind. 6 Monate alt)
  - Transatlantik: Mindestabfahrt 25.10.2026 (Kind mind. 12 Monate alt)

## Installation

```bash
cd cruise-search
pip install -r requirements.txt
playwright install chromium
```

## Konfiguration

`config.json` anpassen:

```json
{
  "budget": { "max_total_eur": 5000 },
  "notification": {
    "email": {
      "enabled": true,
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "deine@email.de",
      "password": "app-passwort",
      "from": "deine@email.de",
      "to": "benachrichtigung@email.de"
    }
  }
}
```

## Starten

```bash
# Daemon (sucht alle 60 Minuten, konfigurierbar)
python main.py

# Einmaliger Suchlauf
python main.py --once

# API-Endpunkte debuggen (zeigt alle intercepted Calls)
python main.py --once --discover

# Anderes Intervall (z.B. alle 30 Minuten)
python main.py --interval 30

# Nur Celebrity Cruises
# → config.json: "cruise_lines": ["celebrity"]
```

## Ausgabe

- **Konsole**: Sofortige Ausgabe gefundener Tarife
- **found_fares.json**: Persistierte Ergebnisse (keine Duplikate)
- **cruise_search.log**: Vollständiges Log
- **E-Mail**: HTML-Tabelle mit allen passenden Tarifen (wenn konfiguriert)

## Hinweise

- Die Scraper nutzen Playwright (Chromium headless) um die JavaScript-lastigen
  Websites zu laden und API-Responses abzufangen.
- Celebrity Cruises und Royal Caribbean aktualisieren ihre APIs regelmäßig.
  `--discover` zeigt alle intercepted API-Calls für Fehlersuche.
- Silversea: Alle Kabinen sind Suiten (≥ Balkon-Level per Definition).
- Bei Silversea ist Internet typischerweise im Preis inbegriffen.
