# Code-Standards: Fitness-Agent

## Python
- **Einrückung**: 4 Spaces
- **Naming**: `snake_case` für Variablen/Funktionen, `UPPER_SNAKE_CASE` für Konstanten.
- **Docstrings**: Google-Style für alle Funktionen.
- **Typisierung**: `Path` für Dateipfade, `Optional`/`Union` für flexible Rückgabewerte.

### Beispiel
```python
from pathlib import Path

def analyze_screenshot(client: genai.Client, image_path: Path) -> dict | None:
    """Analysiert einen Screenshot mit Gemini Vision.

    Args:
        client: Gemini-Client
        image_path: Pfad zum Screenshot

    Returns:
        Extrahierte Trainingsdaten als dict oder None bei Fehler.
    """
    ...
```

## SQLite
- **Transaktionen**: Immer `conn.commit()` nach Schreiboperationen.
- **Schema**: Zentral in `config.py` definiert.
- **Parameterized Queries**: Verhindert SQL-Injection.

### Beispiel
```python
conn.execute(
    """INSERT INTO sessions (datum, disziplin, distanz_m) VALUES (?, ?, ?)""",
    (data["datum"], data["disziplin"], data["distanz_m"])
)
```

## Sicherheitsregeln
- **API-Key**: Niemals im Code oder Git, nur in `.env`.
- **Dateizugriff**: `Path`-Objekte für plattformunabhängige Pfade.
- **Error Handling**: Spezifische Exceptions abfangen (z. B. `json.JSONDecodeError`).

## Git
- **`.gitignore`**:
  ```
  venv/
  .env
  training.db
  __pycache__/
  ```

## Testing
- **Manuelle Checkliste**:
  ```
  [ ] Screenshot-Analyse (Gemini-Antwort valide?)
  [ ] DB-Einträge korrekt gespeichert
  [ ] Dateien nach `verarbeitet/` verschoben
  [ ] Rate-Limit eingehalten
  ```