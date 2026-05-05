"""Konfiguration für den Strava Screenshot Agent."""

import os
from pathlib import Path

# Basis-Pfade
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
SCREENSHOTS_DIR = PROJECT_DIR / "Strava_Screenshots"
PROCESSED_DIR = SCREENSHOTS_DIR / "verarbeitet"
DB_PATH = PROJECT_DIR / "training.db"

# Unterstützte Bildformate
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}

# Gemini Modell
GEMINI_MODEL = "gemini-2.5-flash"

# Prompt für Gemini: Nur Datenextraktion, kein Coaching
GEMINI_PROMPT = """Analysiere diesen Strava-Screenshot und extrahiere die Trainingsdaten.

Der Screenshot ist auf Deutsch. Extrahiere ALLE sichtbaren Daten.

Antworte AUSSCHLIESSLICH mit validem JSON in diesem Format:
{
  "datum": "YYYY-MM-DD",
  "uhrzeit": "HH:MM",
  "aktivitaet_name": "Name der Aktivität aus dem Screenshot",
  "disziplin": "schwimmen|radfahren|laufen|sonstiges",
  "distanz_m": 150,
  "dauer_sekunden": 955,
  "dauer_text": "15:55",
  "tempo": "10:36 /100m",
  "herzfrequenz_avg": 144,
  "kalorien": 187,
  "geraet": "Amazfit T-Rex 2",
  "runden": [
    {
      "nummer": 1,
      "distanz_m": 150,
      "dauer_text": "15:55",
      "tempo": "10:36 /100m",
      "herzfrequenz": 144
    }
  ]
}

Regeln:
- Distanz IMMER in Metern (auch wenn km angezeigt wird: 3.5 km → 3500)
- Dauer IMMER in Sekunden umrechnen (15:55 → 955)
- dauer_text: Originalformat beibehalten ("15:55")
- tempo: Originalformat beibehalten ("10:36 /100m" oder "5:30 /km")
- Disziplin anhand des Aktivitätstyps erkennen (Schwimmen, Radfahrt, Lauf etc.)
- Falls ein Wert nicht sichtbar ist: null setzen
- Falls mehrere Runden sichtbar: alle auflisten
- NUR JSON ausgeben, kein anderer Text
"""

# DB Schema
DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    datum           DATE NOT NULL,
    uhrzeit         TIME,
    aktivitaet_name TEXT,
    disziplin       TEXT NOT NULL,
    distanz_m       REAL,
    dauer_sekunden  INTEGER,
    dauer_text      TEXT,
    tempo           TEXT,
    herzfrequenz_avg INTEGER,
    kalorien        INTEGER,
    geraet          TEXT,
    screenshot      TEXT NOT NULL,
    roh_json        TEXT,
    synced          INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS runden (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(id),
    nummer          INTEGER,
    distanz_m       REAL,
    dauer_text      TEXT,
    tempo           TEXT,
    herzfrequenz    INTEGER
);
"""
