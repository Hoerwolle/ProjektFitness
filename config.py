import os
from pathlib import Path

# Standardpfad mit Fallback
SCREENSHOT_DIR = os.getenv(
    "SCREENSHOT_DIR",
    "/home/bastian/ownCloud/Persönlich/coffeeproject/Projekt Fitness/Strava_Screenshots"
)

def validate_screenshot_dir():
    """Validiert das Screenshot-Verzeichnis und erstellt es bei Bedarf."""
    dir_path = Path(SCREENSHOT_DIR)
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
    if not dir_path.is_dir():
        raise ValueError(f"SCREENSHOT_DIR ist kein Verzeichnis: {dir_path}")
    return str(dir_path.absolute())