"""OCR-Engine-Abstraktion für Tesseract und Gemini.

Features:
- Timeout-Handhabung für Tesseract (verhindert Blockaden)
- Bildvorverarbeitung (Skalierung, Graustufen, Binarisierung)
- Fallback-Logik zu Gemini
- Logging-Integration
- Validierung der Tesseract-Installation
"""

import logging
import signal
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from PIL import Image

# Konfiguration für Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Custom Timeout-Exception für Tesseract."""
    pass


@contextmanager
def timeout_handler(seconds: int):
    """Kontextmanager für Timeout-Handhabung (Unix-only).
    
    Args:
        seconds: Timeout in Sekunden
        
    Raises:
        TimeoutError: Wenn die Operation länger als `seconds` dauert
    """
    def _timeout_handler(signum, frame):
        raise TimeoutError(f"Timeout nach {seconds} Sekunden")

    # Nur auf Unix-Systemen verfügbar
    if hasattr(signal, 'SIGALRM'):
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(seconds)
    try:
        yield
    finally:
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)


class OCREngine(ABC):
    """Abstraktes Interface für OCR-Engines."""

    @abstractmethod
    def extract_text(self, image_path: Path) -> Optional[str]:
        """Extrahiert Rohtext aus einem Bild.

        Args:
            image_path: Pfad zum Screenshot.

        Returns:
            Extrahierter Text oder None bei Fehler.
        """
        pass


class TesseractEngine(OCREngine):
    """Tesseract OCR-Engine mit Vorverarbeitung und Timeout."""

    def __init__(
        self,
        config: str = "--psm 6 --oem 3",
        lang: str = "deu+eng",
        timeout: int = 30,
        max_width: int = 2000,
    ):
        """Initialisiert Tesseract-Engine.

        Args:
            config: Tesseract-Konfigurationsstring (z. B. "--psm 6 --oem 3").
            lang: Sprachmodell (z. B. "deu+eng").
            timeout: Timeout in Sekunden (Default: 30).
            max_width: Maximale Breite für Bildskalierung (Default: 2000px).
        """
        self.config = config
        self.lang = lang
        self.timeout = timeout
        self.max_width = max_width
        self._validate_tesseract()

    def _validate_tesseract(self) -> None:
        """Prüft, ob Tesseract installiert ist.
        
        Raises:
            RuntimeError: Wenn Tesseract nicht verfügbar ist
        """
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            logger.info("Tesseract-Validierung: OK")
        except Exception as e:
            logger.error(
                "Tesseract nicht installiert oder nicht in PATH. "
                "Installiere mit: sudo apt install tesseract-ocr tesseract-ocr-deu "
                "tesseract-ocr-eng libtesseract-dev"
            )
            raise RuntimeError(f"Tesseract nicht verfügbar: {e}") from e

    def _preprocess_image(self, img: Image.Image) -> Image.Image:
        """Führt Bildvorverarbeitung durch.

        Schritte:
        1. Skalierung auf max_width (falls größer)
        2. Konvertierung zu Graustufen
        3. Binarisierung (Schwellwert: 150)
        
        Args:
            img: PIL.Image-Objekt
            
        Returns:
            Vorverarbeitetes Bild
        """
        # Skalierung (falls Bild zu groß)
        if img.width > self.max_width:
            ratio = self.max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
            logger.debug(f"Bild skaliert von {img.width}x{img.height} auf {self.max_width}x{new_height}")

        # Graustufen
        img = img.convert("L")

        # Binarisierung (Schwellwert 150)
        img = img.point(lambda x: 0 if x < 150 else 255)

        return img

    def extract_text(self, image_path: Path) -> Optional[str]:
        """Extrahiert Text mit Tesseract und Timeout-Handhabung.

        Args:
            image_path: Pfad zum Screenshot
            
        Returns:
            Extrahierter Text oder None bei Fehler
        """
        import pytesseract

        try:
            # Bild laden
            img = Image.open(image_path)
            img = self._preprocess_image(img)

            # Timeout-Handhabung
            try:
                with timeout_handler(self.timeout):
                    text = pytesseract.image_to_string(
                        img,
                        config=self.config,
                        lang=self.lang,
                    )
            except TimeoutError:
                logger.warning(
                    f"Tesseract-Timeout für {image_path.name} nach {self.timeout}s"
                )
                return None

            if text and text.strip():
                logger.debug(f"Tesseract extrahiert {len(text)} Zeichen aus {image_path.name}")
                return text.strip()
            else:
                logger.warning(f"Tesseract lieferte leeren Text für {image_path.name}")
                return None

        except pytesseract.TesseractNotFound as e:
            logger.error(f"Tesseract nicht gefunden: {e}")
            return None
        except Exception as e:
            logger.error(f"Tesseract-Fehler bei {image_path.name}: {e}")
            return None


class GeminiEngine(OCREngine):
    """Gemini Vision API-Engine (Fallback)."""

    def __init__(
        self,
        client,
        prompt: str,
        model: str = "gemini-2.5-flash",
    ):
        """Initialisiert Gemini-Engine.

        Args:
            client: Google GenAI Client.
            prompt: Prompt für die Datenextraktion.
            model: Modellname (Default: gemini-2.5-flash).
        """
        self.client = client
        self.prompt = prompt
        self.model = model

    def extract_text(self, image_path: Path) -> Optional[str]:
        """Extrahiert Text mit Gemini Vision API.

        Args:
            image_path: Pfad zum Screenshot
            
        Returns:
            Extrahierter Text oder None bei Fehler
        """
        from google import genai

        try:
            image_bytes = image_path.read_bytes()
            mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    self.prompt,
                    genai.types.Part.from_bytes(data=image_bytes, mime_type=mime),
                ],
            )
            text = response.text.strip() if response.text else None
            if text:
                logger.debug(f"Gemini extrahiert {len(text)} Zeichen aus {image_path.name}")
            return text
        except Exception as e:
            logger.error(f"Gemini-Fehler bei {image_path.name}: {e}")
            return None
