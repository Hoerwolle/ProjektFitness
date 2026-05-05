"""Unit-Tests für die neue OCR-Bildverarbeitung."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from ocr_engine import TesseractEngine, GeminiEngine, TimeoutError
from parser import (
    parse_training_data,
    extract_date,
    extract_time,
    extract_distanz,
    extract_dauer_sekunden,
    extract_disziplin,
    extract_herzfrequenz,
    extract_kalorien,
    extract_runden,
    extract_notizen,
    sanitize_string,
)

# Testdaten-Verzeichnis
TEST_DIR = Path("~/opencloud/coffeeproject/Projekt Fitness/Strava_Screenshots/verarbeitet").expanduser()


# --- Tests für parser.py ---
class TestParser:
    """Tests für den Parser."""

    def test_sanitize_string(self):
        assert sanitize_string("Test") == "Test"
        assert sanitize_string("Test' OR '1'='1") == "Test'' OR ''1''=''1"
        assert sanitize_string(None) is None

    def test_extract_date_de_format(self):
        assert extract_date("Datum: 05.05.2026") == "2026-05-05"
        assert extract_date("05.05.2026") == "2026-05-05"
        assert extract_date("5.5.2026") == "2026-05-05"

    def test_extract_date_iso_format(self):
        assert extract_date("2026-05-05") == "2026-05-05"

    def test_extract_date_text_format(self):
        assert extract_date("5 Mai 2026") == "5 Mai 2026"

    def test_extract_date_none(self):
        assert extract_date("Kein Datum") is None

    def test_extract_time(self):
        assert extract_time("Zeit: 18:30") == "18:30"
        assert extract_time("18:30:45") == "18:30"  # Nimmt nur HH:MM
        assert extract_time("Keine Zeit") is None

    def test_extract_distanz_km(self):
        assert extract_distanz("3,5 km") == 3500.0
        assert extract_distanz("3.5 km") == 3500.0
        assert extract_distanz("1500 Meter") == 1500.0

    def test_extract_distanz_m(self):
        assert extract_distanz("1500 m") == 1500.0

    def test_extract_dauer_sekunden(self):
        assert extract_dauer_sekunden("Dauer: 45:00") == 2700
        assert extract_dauer_sekunden("Duration: 1:30:00") == 5400
        assert extract_dauer_sekunden("Dauer: 955s") == 955

    def test_extract_disziplin(self):
        assert extract_disziplin("Schwimmen") == "schwimmen"
        assert extract_disziplin("Radfahren") == "radfahren"
        assert extract_disziplin("Laufen") == "laufen"
        assert extract_disziplin("Sonstiges") == "sonstiges"
        assert extract_disziplin("Swimming") == "schwimmen"
        assert extract_disziplin("Cycling") == "radfahren"

    def test_extract_herzfrequenz(self):
        assert extract_herzfrequenz("Herzfrequenz: 144") == 144
        assert extract_herzfrequenz("HF: 144") == 144
        assert extract_herzfrequenz("Puls: 144") == 144
        assert extract_herzfrequenz("Heart Rate: 144") == 144
        assert extract_herzfrequenz("Herzfrequenz: 250") is None  # Plausibilitätscheck

    def test_extract_kalorien(self):
        assert extract_kalorien("Kalorien: 350") == 350
        assert extract_kalorien("kcal: 350") == 350
        assert extract_kalorien("Energy: 350") == 350

    def test_extract_runden(self):
        text = "Runde 1: 500m in 15:00, Runde 2: 1000m in 30:00"
        runden = extract_runden(text)
        assert len(runden) == 2
        assert runden[0]["nummer"] == 1
        assert runden[0]["distanz_m"] == 500.0
        assert runden[0]["dauer_text"] == "15:00"

    def test_extract_notizen(self):
        text = "Notizen: Gutes Training!\n\nDatum: 05.05.2026"
        assert extract_notizen(text) == "Gutes Training!"

    def test_parse_training_data(self):
        text = "Datum: 05.05.2026, Zeit: 18:30, Distanz: 3,5 km, Dauer: 45:00, Disziplin: Schwimmen"
        data = parse_training_data(text)
        assert data["datum"] == "2026-05-05"
        assert data["uhrzeit"] == "18:30"
        assert data["distanz_m"] == 3500.0
        assert data["dauer_sekunden"] == 2700  # 45 Minuten = 2700 Sekunden
        assert data["disziplin"] == "schwimmen"
        assert data["roh_text"] == text  # sanitize_string ändert nichts bei diesem Text


# --- Tests für ocr_engine.py ---
class TestOCREngine:
    """Tests für die OCR-Engine."""

    def test_tesseract_engine_init(self):
        engine = TesseractEngine()
        assert engine.config == "--psm 6 --oem 3"
        assert engine.lang == "deu+eng"
        assert engine.timeout == 30
        assert engine.max_width == 2000

    @patch("pytesseract.get_tesseract_version")
    def test_tesseract_engine_validation(self, mock_version):
        mock_version.side_effect = Exception("Tesseract not found")
        with pytest.raises(RuntimeError):
            TesseractEngine()

    @patch("pytesseract.image_to_string")
    def test_tesseract_extract_text(self, mock_pytesseract):
        mock_pytesseract.return_value = "Testtext"
        engine = TesseractEngine()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img = Image.new("RGB", (100, 100), color="white")
            img.save(tmp.name)
            tmp_path = Path(tmp.name)

        result = engine.extract_text(tmp_path)
        assert result == "Testtext"
        tmp_path.unlink()  # Cleanup

    @patch("pytesseract.image_to_string")
    def test_tesseract_timeout(self, mock_pytesseract):
        mock_pytesseract.side_effect = TimeoutError("Timeout")
        engine = TesseractEngine(timeout=1)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img = Image.new("RGB", (100, 100), color="white")
            img.save(tmp.name)
            tmp_path = Path(tmp.name)

        result = engine.extract_text(tmp_path)
        assert result is None
        tmp_path.unlink()  # Cleanup

    def test_gemini_engine_init(self):
        mock_client = MagicMock()
        engine = GeminiEngine(mock_client, "Prompt")
        assert engine.client == mock_client
        assert engine.prompt == "Prompt"
        assert engine.model == "gemini-2.5-flash"


# --- Integrationstests ---
class TestIntegration:
    """Integrationstests für OCR + Parser."""

    @patch("pytesseract.image_to_string")
    def test_full_pipeline(self, mock_pytesseract):
        mock_pytesseract.return_value = (
            "Datum: 05.05.2026\n"
            "Zeit: 18:30\n"
            "Distanz: 3,5 km\n"
            "Dauer: 45:00\n"
            "Disziplin: Schwimmen"
        )
        engine = TesseractEngine()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img = Image.new("RGB", (100, 100), color="white")
            img.save(tmp.name)
            tmp_path = Path(tmp.name)

        raw_text = engine.extract_text(tmp_path)
        data = parse_training_data(raw_text)
        assert data["datum"] == "2026-05-05"
        assert data["disziplin"] == "schwimmen"
        tmp_path.unlink()  # Cleanup


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
