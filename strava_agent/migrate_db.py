"""Migration für die neue Bildverarbeitung.

Fügt die Spalte `roh_text` zur `sessions`-Tabelle hinzu und füllt sie
für bestehende Einträge nachträglich.
"""

import sqlite3
from pathlib import Path

from config import DB_PATH, PROCESSED_DIR, SCREENSHOTS_DIR
from ocr_engine import TesseractEngine


def migrate_db():
    """Fügt `roh_text` zur DB hinzu und füllt bestehende Einträge."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Spalte hinzufügen (falls nicht vorhanden)
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [row[1] for row in cursor.fetchall()]
    if "roh_text" not in columns:
        cursor.execute("ALTER TABLE sessions ADD COLUMN roh_text TEXT")
        conn.commit()
        print("✓ Spalte 'roh_text' hinzugefügt.")
    else:
        print("✓ Spalte 'roh_text' existiert bereits.")

    # Bestehende Einträge ohne roh_text nachträglich füllen
    cursor.execute("SELECT id, screenshot FROM sessions WHERE roh_text IS NULL OR roh_text = ''")
    missing_entries = cursor.fetchall()
    print(f"✓ {len(missing_entries)} Einträge ohne roh_text gefunden.")

    if missing_entries:
        engine = TesseractEngine()
        for entry_id, screenshot_name in missing_entries:
            # Screenshot finden
            screenshot_path = None
            for dir_path in [SCREENSHOTS_DIR, PROCESSED_DIR]:
                path = dir_path / screenshot_name
                if path.exists():
                    screenshot_path = path
                    break

            if screenshot_path:
                raw_text = engine.extract_text(screenshot_path)
                if raw_text:
                    cursor.execute(
                        "UPDATE sessions SET roh_text = ? WHERE id = ?",
                        (raw_text, entry_id),
                    )
                    print(f"  ✓ Rohtext für {screenshot_name} hinzugefügt.")
                else:
                    print(f"  ⚠ Warnung: Rohtext für {screenshot_name} konnte nicht extrahiert werden.")
            else:
                print(f"  ⚠ Warnung: Screenshot {screenshot_name} nicht gefunden.")

        conn.commit()
        print("✓ Migration der Rohtexte abgeschlossen.")

    conn.close()
    print("✓ Migration vollständig abgeschlossen.")


if __name__ == "__main__":
    migrate_db()
