"""Parser für die Extraktion strukturierter Trainingsdaten aus OCR-Rohtext.

Features:
- Robuste Regex-Patterns für deutsche/englische Screenshots
- Validierung der extrahierten Daten
- Unterstützung für unstrukturierte Notizen
- SQL-Injection-Schutz durch Sanitization
"""

import re
from typing import Optional


def sanitize_string(value: Optional[str]) -> Optional[str]:
    """Sanitized String für DB-Einträge (verhindert SQL-Injection).
    
    Args:
        value: Zu sanitizender String
        
    Returns:
        Sanitizierter String oder None
    """
    if value is None:
        return None
    # Ersetze einfache Anführungszeichen, um SQL-Injection zu verhindern
    return value.replace("'", "''").strip()


def parse_training_data(raw_text: str) -> dict:
    """Parsed Rohtext von Tesseract/Gemini in strukturierte Trainingsdaten.

    Args:
        raw_text: Rohtext aus OCR-Engine.

    Returns:
        Dictionary mit extrahierten Trainingsdaten.
    """
    data = {
        "datum": extract_date(raw_text),
        "uhrzeit": extract_time(raw_text),
        "aktivitaet_name": sanitize_string(extract_aktivitaet_name(raw_text)),
        "disziplin": extract_disziplin(raw_text),
        "distanz_m": extract_distanz(raw_text),
        "dauer_sekunden": extract_dauer_sekunden(raw_text),
        "dauer_text": sanitize_string(extract_dauer_text(raw_text)),
        "tempo": sanitize_string(extract_tempo(raw_text)),
        "herzfrequenz_avg": extract_herzfrequenz(raw_text),
        "kalorien": extract_kalorien(raw_text),
        "geraet": sanitize_string(extract_geraet(raw_text)),
        "runden": extract_runden(raw_text),
        "notizen": sanitize_string(extract_notizen(raw_text)),
        "roh_text": sanitize_string(raw_text),
    }
    return data


def extract_date(text: str) -> Optional[str]:
    """Extrahiert Datum im Format YYYY-MM-DD.

    Unterstützte Formate:
    - ISO: 2026-05-05
    - DE: 05.05.2026 oder 5.5.2026
    - Text: 5 Mai 2026
    
    Args:
        text: Rohtext
        
    Returns:
        Datum im Format YYYY-MM-DD oder None
    """
    patterns = [
        (r"(\d{4}-\d{2}-\d{2})", "iso"),  # ISO-Format
        (r"(\d{1,2}\.\d{1,2}\.\d{4})", "de"),  # DE-Format (TT.MM.JJJJ)
        (r"(\d{1,2}\s+[A-Za-zäöüß]+\s+\d{4})", "text"),  # Textformat
    ]

    for pattern, fmt in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            if fmt == "iso":
                return date_str
            elif fmt == "de":
                parts = date_str.split(".")
                day = parts[0].zfill(2)
                month = parts[1].zfill(2)
                year = parts[2]
                return f"{year}-{month}-{day}"
            elif fmt == "text":
                # Vereinfacht: Nimm das erste gefundene Datum
                return date_str
    return None


def extract_time(text: str) -> Optional[str]:
    """Extrahiert Uhrzeit im Format HH:MM.
    
    Args:
        text: Rohtext
        
    Returns:
        Uhrzeit im Format HH:MM oder None
    """
    # Suche nach HH:MM oder HH:MM:SS und nimm die ersten beiden Teile
    match = re.search(r"(\d{1,2}:\d{2})(?::\d{2})?", text)
    return match.group(1) if match else None


def extract_aktivitaet_name(text: str) -> Optional[str]:
    """Extrahiert den Namen der Aktivität.
    
    Args:
        text: Rohtext
        
    Returns:
        Name der Aktivität oder None
    """
    patterns = [
        r"(?:Aktivität|Activity|Name|Titel|Title)\s*[:]?\s*(.+?)(?:\n|$)",
        r"^(?!.+?:\s*)(.+?)(?=\n)",  # Erste Zeile, falls kein Label
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            # Filtere unerwünschte Keywords heraus
            keywords = ["datum", "zeit", "distanz", "dauer", "tempo", "herzfrequenz"]
            if not any(kw in name.lower() for kw in keywords):
                return name
    return None


def extract_disziplin(text: str) -> str:
    """Extrahiert Disziplin (schwimmen, radfahren, laufen, sonstiges).
    
    Args:
        text: Rohtext
        
    Returns:
        Disziplin als String
    """
    disziplinen = {
        "schwimmen": ["schwimmen", "swim", "pool", "bahn", "swimming", "kraulen", "brust"],
        "radfahren": ["radfahren", "rad", "bike", "fahrrad", "cycling", "velo", "rennrad"],
        "laufen": ["laufen", "lauf", "run", "joggen", "jogging", "running", "marathon"],
    }
    text_lower = text.lower()
    for disziplin, keywords in disziplinen.items():
        if any(keyword in text_lower for keyword in keywords):
            return disziplin
    return "sonstiges"


def extract_distanz(text: str) -> Optional[float]:
    """Extrahiert Distanz in Metern.

    Unterstützte Formate:
    - 3,5 km → 3500.0
    - 1500 m → 1500.0
    - 1.500 Meter → 1500.0
    - 3.5km → 3500.0
    
    Args:
        text: Rohtext
        
    Returns:
        Distanz in Metern oder None
    """
    patterns = [
        (r"(\d+[.,]?\d*)\s*(?:km|Kilometer)", 1000),  # Kilometer → *1000
        (r"(\d+[.,]?\d*)\s*(?:m|Meter)", 1),  # Meter → *1
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1).replace(",", "."))
            return value * multiplier
    return None


def extract_dauer_sekunden(text: str) -> Optional[int]:
    """Extrahiert Dauer in Sekunden.

    Unterstützte Formate:
    - 45:00 → 2700 (MM:SS)
    - 1:30:00 → 5400 (HH:MM:SS)
    - 955s → 955
    
    Args:
        text: Rohtext
        
    Returns:
        Dauer in Sekunden oder None
    """
    # Suche nach Dauer in der Nähe von Keywords wie "Dauer", "Duration"
    # Format: HH:MM:SS
    match = re.search(r"(?:Dauer|Duration)\D*(\d{1,2}):(\d{2}):(\d{2})\b", text, re.IGNORECASE)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        if hours < 24 and minutes < 60 and seconds < 60:
            return hours * 3600 + minutes * 60 + seconds
    
    # Format: MM:SS
    match = re.search(r"(?:Dauer|Duration)\D*(\d{1,2}):(\d{2})\b", text, re.IGNORECASE)
    if match:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        if minutes < 60 and seconds < 60:
            return minutes * 60 + seconds
    
    # Sekunden direkt
    match = re.search(r"(?:Dauer|Duration)\D*(\d+)\s*s", text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def extract_dauer_text(text: str) -> Optional[str]:
    """Extrahiert Dauer im Originalformat (z. B. '45:00' oder '1:30:00').
    
    Args:
        text: Rohtext
        
    Returns:
        Dauer im Originalformat oder None
    """
    match = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?)", text)
    return match.group(1) if match else None


def extract_tempo(text: str) -> Optional[str]:
    """Extrahiert Tempo im Originalformat.

    Unterstützte Formate:
    - 3:00 /100m
    - 5:30 /km
    - 10:36/min
    
    Args:
        text: Rohtext
        
    Returns:
        Tempo im Originalformat oder None
    """
    match = re.search(
        r"(\d{1,2}:\d{2}\s*(?:/\d+[mkm]|/min|min))",
        text,
    )
    return match.group(1) if match else None


def extract_herzfrequenz(text: str) -> Optional[int]:
    """Extrahiert durchschnittliche Herzfrequenz.
    
    Unterstützte Formate:
    - Herzfrequenz: 144
    - HF: 144
    - Puls: 144
    - Heart Rate: 144
    - ❤️ 144
    
    Args:
        text: Rohtext
        
    Returns:
        Herzfrequenz (30-220) oder None
    """
    match = re.search(
        r"(?:Herzfrequenz|HF|Puls|Heart Rate|HR|❤️)\D*(\d{2,3})",
        text,
        re.IGNORECASE,
    )
    if match:
        hf = int(match.group(1))
        # Plausibilitätscheck: Herzfrequenz zwischen 30 und 220
        return hf if 30 <= hf <= 220 else None
    return None


def extract_kalorien(text: str) -> Optional[int]:
    """Extrahiert Kalorien.
    
    Unterstützte Formate:
    - Kalorien: 350
    - kcal: 350
    - Energy: 350
    - Energie: 350
    
    Args:
        text: Rohtext
        
    Returns:
        Kalorien oder None
    """
    match = re.search(
        r"(?:Kalorien|kcal|Energy|Energie)\D*(\d+)",
        text,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def extract_geraet(text: str) -> Optional[str]:
    """Extrahiert Gerätename.
    
    Unterstützte Formate:
    - Gerät: Garmin Swim 2
    - Device: Amazfit T-Rex 2
    - Uhr: Apple Watch
    - Tracked with: Garmin Forerunner
    
    Args:
        text: Rohtext
        
    Returns:
        Gerätename oder None
    """
    patterns = [
        r"(?:Gerät|Device|Uhr|Watch|Tracked with|Aufgezeichnet mit)\D*[:]?\s*(.+?)(?:\n|$)",
        r"(?:Garmin|Amazfit|Apple Watch|Polar|Suunto|Coros)\s*([A-Za-z0-9\s]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_runden(text: str) -> list[dict]:
    """Extrahiert Rundendaten.

    Unterstützte Formate:
    - Runde 1: 500m in 15:00
    - Round 1: 500m 15:00
    - Lap 1 500m 15:00:00
    
    Args:
        text: Rohtext
        
    Returns:
        Liste von Rundendaten oder leere Liste
    """
    runden = []
    pattern = r"(?:Runde|Round|Lap)\D*(\d+)\D*(\d+[.,]?\d*)\s*(?:m|Meter|km)\D*(\d{1,2}:\d{2}(?::\d{2})?)"

    for match in re.finditer(pattern, text, re.IGNORECASE):
        distanz = float(match.group(2).replace(",", "."))
        unit = match.group(0).lower()
        if "km" in unit:
            distanz *= 1000
        runden.append({
            "nummer": int(match.group(1)),
            "distanz_m": distanz,
            "dauer_text": match.group(3),
            "tempo": extract_tempo(match.group(0)),  # Versuche Tempo zu extrahieren
            "herzfrequenz": extract_herzfrequenz(match.group(0)),  # Versuche HF zu extrahieren
        })

    return runden if runden else []


def extract_notizen(text: str) -> Optional[str]:
    """Extrahiert unstrukturierte Notizen/Kommentare.
    
    Unterstützte Formate:
    - Notizen: Gutes Training!
    - Kommentar: Sehr anstrengend
    - Beschreibung: Lange Einheit
    
    Args:
        text: Rohtext
        
    Returns:
        Notizen oder None
    """
    # Explizite Markierungen
    patterns = [
        r"(?:Notizen|Kommentar|Bemerkung|Notes|Comment|Beschreibung|Description)\s*[:]?\s*(.+?)(?:\n\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

    # Letzter Absatz (falls keine Markierung)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        last_para = paragraphs[-1]
        # Prüfe, ob es sich um strukturierte Daten handelt
        structured_keywords = [
            "datum", "zeit", "distanz", "dauer", "tempo", "herzfrequenz",
            "kalorien", "gerät", "runde", "disziplin", "aktivität"
        ]
        if not any(keyword in last_para.lower() for keyword in structured_keywords):
            return last_para
    return None
