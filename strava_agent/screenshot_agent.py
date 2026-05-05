#!/usr/bin/env python3
"""Strava Screenshot Agent - Extrahiert Trainingsdaten via Gemini Vision."""

import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from config import (
    DB_PATH,
    DB_SCHEMA,
    GEMINI_MODEL,
    GEMINI_PROMPT,
    IMAGE_EXTENSIONS,
    PROCESSED_DIR,
    SCREENSHOTS_DIR,
)

# Rate-Limit: Pause zwischen API-Calls (Sekunden)
API_DELAY = 4
# Max Retries bei 429/5xx Fehlern
MAX_RETRIES = 3


def init_db(db_path: Path) -> sqlite3.Connection:
    """Erstellt die DB und Tabellen falls noetig."""
    is_new = not db_path.exists()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(DB_SCHEMA)
    conn.commit()
    if is_new:
        print(f"Neue Datenbank erstellt: {db_path.name}")
    return conn


def get_known_screenshots(conn: sqlite3.Connection) -> set[str]:
    """Liefert alle bereits importierten Screenshot-Dateinamen."""
    cursor = conn.execute("SELECT screenshot FROM sessions")
    return {row[0] for row in cursor.fetchall()}


def find_new_screenshots(known: set[str]) -> list[Path]:
    """Findet neue Screenshots in beiden Verzeichnissen."""
    new_files = []

    # Neue (noch nicht verschobene) Screenshots
    if SCREENSHOTS_DIR.exists():
        for f in SCREENSHOTS_DIR.iterdir():
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS and f.name not in known:
                new_files.append(f)

    # Bereits verschobene, aber noch nicht in DB (Migration)
    if PROCESSED_DIR.exists():
        for f in PROCESSED_DIR.iterdir():
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS and f.name not in known:
                new_files.append(f)

    new_files.sort(key=lambda f: f.name)
    return new_files


def analyze_screenshot(client: genai.Client, image_path: Path) -> dict | None:
    """Sendet Screenshot an Gemini und extrahiert Trainingsdaten."""
    print(f"  Analysiere: {image_path.name} ...", end=" ", flush=True)

    image_bytes = image_path.read_bytes()
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    GEMINI_PROMPT,
                    genai.types.Part.from_bytes(data=image_bytes, mime_type=mime),
                ],
            )
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "ResourceExhausted" in err_str:
                wait = API_DELAY * (2 ** attempt)
                print(f"Rate-Limit, warte {wait}s ...", end=" ", flush=True)
                time.sleep(wait)
                if attempt == MAX_RETRIES:
                    print("FEHLER (Rate-Limit)")
                    return None
            else:
                print(f"FEHLER ({e})")
                return None

    raw_text = response.text.strip()

    # JSON aus Antwort extrahieren (Gemini wraps manchmal in ```json...```)
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])

    try:
        data = json.loads(raw_text)
        print("OK")
        return data
    except json.JSONDecodeError as e:
        print(f"FEHLER (JSON ungueltig: {e})")
        print(f"  Gemini-Antwort: {raw_text[:200]}")
        return None


def save_to_db(conn: sqlite3.Connection, data: dict, screenshot_name: str, raw_json: str):
    """Speichert extrahierte Daten in die DB."""
    cursor = conn.execute(
        """INSERT INTO sessions
           (datum, uhrzeit, aktivitaet_name, disziplin, distanz_m,
            dauer_sekunden, dauer_text, tempo, herzfrequenz_avg,
            kalorien, geraet, screenshot, roh_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("datum"),
            data.get("uhrzeit"),
            data.get("aktivitaet_name"),
            data.get("disziplin", "sonstiges"),
            data.get("distanz_m"),
            data.get("dauer_sekunden"),
            data.get("dauer_text"),
            data.get("tempo"),
            data.get("herzfrequenz_avg"),
            data.get("kalorien"),
            data.get("geraet"),
            screenshot_name,
            raw_json,
        ),
    )
    session_id = cursor.lastrowid

    for runde in data.get("runden", []):
        conn.execute(
            """INSERT INTO runden
               (session_id, nummer, distanz_m, dauer_text, tempo, herzfrequenz)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                runde.get("nummer"),
                runde.get("distanz_m"),
                runde.get("dauer_text"),
                runde.get("tempo"),
                runde.get("herzfrequenz"),
            ),
        )

    conn.commit()
    return session_id


def move_to_processed(image_path: Path):
    """Verschiebt Screenshot nach verarbeitet/ (nur wenn er noch nicht dort ist)."""
    if image_path.parent == PROCESSED_DIR:
        return  # Bereits im verarbeitet-Ordner (Migration)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dest = PROCESSED_DIR / image_path.name
    shutil.move(str(image_path), str(dest))
    print(f"  Verschoben nach: verarbeitet/{image_path.name}")


def main():
    # .env laden
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("FEHLER: Bitte GEMINI_API_KEY in .env setzen!")
        print(f"  Datei: {env_path}")
        sys.exit(1)

    # Gemini Client erstellen (neues SDK)
    client = genai.Client(api_key=api_key)

    # DB initialisieren
    conn = init_db(DB_PATH)
    known = get_known_screenshots(conn)

    # Neue Screenshots finden
    new_files = find_new_screenshots(known)

    if not new_files:
        print("Keine neuen Screenshots gefunden.")
        conn.close()
        return

    print(f"{len(new_files)} neue Screenshot(s) gefunden.\n")

    imported = 0
    errors = 0

    for i, image_path in enumerate(new_files):
        # Rate-Limit: Pause zwischen Calls (nicht vor dem ersten)
        if i > 0:
            time.sleep(API_DELAY)

        data = analyze_screenshot(client, image_path)

        if data is None:
            errors += 1
            continue

        raw_json = json.dumps(data, ensure_ascii=False, indent=2)
        save_to_db(conn, data, image_path.name, raw_json)
        move_to_processed(image_path)
        imported += 1

    conn.close()

    print(f"\nFertig: {imported} importiert, {errors} Fehler.")


if __name__ == "__main__":
    main()
