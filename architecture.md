# Architektur: Fitness-Tracking-Agent

## Grundprinzipien
- **Dateibasierte Persistenz**: SQLite-Datenbank (`training.db`) für Trainingsdaten.
- **Single-User**: Keine Benutzerverwaltung, lokale Nutzung.
- **Minimale Dependencies**: Nur `google-genai`, `sqlite3`, `python-dotenv`.
- **Verarbeitungsflow**:
  ```
  Screenshots/ → Gemini Vision API → SQLite → verarbeitet/
  ```

## Komponenten
- **`screenshot_agent.py`**: Hauptlogik (API-Calls, DB, Dateimanagement).
- **`config.py`**: Konfiguration (DB-Schema, Prompt, Pfade).
- **`.env`**: API-Key für Gemini.

## Datenmodell
### SQLite-Tabellen
- **`sessions`**: Trainingsdaten (Datum, Disziplin, Distanz, Dauer, etc.).
- **`runden`**: Rundendetails (Nummer, Distanz, Dauer, Tempo).

### Beispiel-Datensatz
```json
{
  "datum": "2025-11-12",
  "disziplin": "schwimmen",
  "distanz_m": 1500,
  "dauer_sekunden": 955,
  "runden": [
    {
      "nummer": 1,
      "distanz_m": 150,
      "dauer_text": "15:55"
    }
  ]
}
```

## Fehlerbehandlung
- **Rate-Limit**: 4-Sekunden-Pause zwischen API-Calls.
- **Retries**: 3 Versuche bei 429/5xx-Fehlern.
- **DB-Transaktionen**: `conn.commit()` nach jedem Schreibvorgang.

## Sicherheit
- **API-Key**: Niemals im Code oder Git, nur in `.env`.
- **Dateizugriff**: `Path`-Objekte für plattformunabhängige Pfade.
- **DB-Berechtigungen**: `chmod 644 training.db`.