# Produkt: Fitness-Tracking-Agent

## Übersicht
Extraktion von Trainingsdaten aus **Strava-Screenshots** via **Gemini Vision API** und Speicherung in **SQLite**. Automatisierte Verarbeitung für Schwimmen, Radfahren, Laufen.

## Tech-Stack
| Komponente       | Technologie               |
|------------------|---------------------------|
| **OCR/API**      | Gemini Vision (gemini-2.5-flash) |
| **Datenbank**    | SQLite (`training.db`)    |
| **Sprache**      | Python 3.10+              |
| **Dependencies** | `google-genai`, `python-dotenv` |

## Projektstruktur
```
/Projekt Fitness/agent/strava_agent/
├── config.py          # Konfiguration (DB-Schema, Prompt, Pfade)
├── screenshot_agent.py # Hauptskript (API, DB, Dateimanagement)
├── .env               # API-Key (GEMINI_API_KEY)
├── requirements.txt   # Abhängigkeiten
├── Strava_Screenshots/ # Eingabeverzeichnis
│   └── verarbeitet/    # Ausgabeverzeichnis
└── training.db        # SQLite-Datenbank
```

## Hauptfunktionen
1. **Screenshot-Analyse**:
   - Extraktion von Datum, Disziplin, Distanz, Dauer, Tempo, Herzfrequenz.
   - Unterstützung für Runden (z. B. Bahnen beim Schwimmen).

2. **Datenbank**:
   - Tabellen: `sessions` (Trainingsdaten), `runden` (Rundendetails).
   - JSON-Rohdaten werden in `roh_json` gespeichert.

3. **Dateimanagement**:
   - Verarbeitete Screenshots werden nach `verarbeitet/` verschoben.

## Deployment
### Voraussetzungen
- Python 3.10+
- `pip install -r requirements.txt`
- `.env` mit `GEMINI_API_KEY`

### Ausführung
```bash
python screenshot_agent.py
```

### Verzeichnisberechtigungen
```bash
chmod 755 Strava_Screenshots/
chmod 644 training.db
```

## Beispiel-Datensatz
```json
{
  "datum": "2025-11-12",
  "uhrzeit": "18:30",
  "aktivitaet_name": "Abendtraining",
  "disziplin": "schwimmen",
  "distanz_m": 1500,
  "dauer_sekunden": 2700,
  "dauer_text": "45:00",
  "tempo": "3:00 /100m",
  "herzfrequenz_avg": 130,
  "kalorien": 350,
  "geraet": "Garmin Swim 2",
  "runden": [
    {
      "nummer": 1,
      "distanz_m": 500,
      "dauer_text": "15:00",
      "tempo": "3:00 /100m"
    }
  ]
}
```

## GitHub-Repository
Lokal in `~/opencloud/coffeeproject/Projekt Fitness/agent/`.

## Roadmap
- [ ] Integration mit Strava API für automatischen Abgleich.
- [ ] Export nach CSV/Excel.
- [ ] Dashboard für Trainingsstatistiken.