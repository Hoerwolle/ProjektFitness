---
name: Umzug und Rework des Fitness-Agenten
status: refined
---

## **Zusammenfassung**
Der bestehende Fitness-Agent wird in ein neues Git-Repository umgezogen und technisch überarbeitet. Ziel ist eine saubere Trennung von Code, Datenbank und Nutzerdaten sowie die Vorbereitung für zukünftige Erweiterungen.

---

## **Details**

### **1. Umzug des Agenten**
- **Quellverzeichnis:**
  `/home/bastian/ownCloud/Persönlich/coffeeproject/Projekt Fitness/agent`
- **Zielverzeichnis:**
  `/home/git/ProjektFitness`
- **Git-Repository:**
  `https://github.com/Hoerwolle/ProjektFitness.git`
  - **Ausschluss:** Die lokale Datenbank wird im Zielverzeichnis abgelegt, aber **nicht** in das Repository committed.

### **2. Konfiguration der Screenshot-Verzeichnisse**
- **Aktuelles Verzeichnis:**
  `/home/bastian/ownCloud/Persönlich/coffeeproject/Projekt Fitness/Strava_Screenshots`
- **Anforderung:**
  - Pfad muss als **konfigurierbare Variable** im Agenten hinterlegt werden.
  - Standardwert: Wie oben, aber **über Umgebungsvariable oder Konfigurationsdatei** überschreibbar.

### **3. Anpassung der Dokumentation**
- **Pfad der Markdown-Dateien:**
  `/home/bastian/ownCloud/Persönlich/coffeeproject/Projekt CodeBender/Resources Fitness/`
- **Aktionen:**
  - Alle Referenzen zu alten Pfaden aktualisieren.
  - Neue Struktur und Variablen dokumentieren.

---

## **Technische Anforderungen**
1. **Git-Struktur:**
   - `.gitignore` anpassen, um die lokale Datenbank auszuschließen.
   - Beispiel:
     ```
     # .gitignore
     /database/*
     !/database/.gitkeep
     ```
2. **Konfigurationsmanagement:**
   - Variable für Screenshot-Pfad in `config.py` oder `settings.json` auslagern.
   - Beispiel:
     ```python
     # config.py
     SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "/default/path")
     ```
3. **Dokumentation:**
   - `README.md` um Abschnitt "Umzug und Konfiguration" erweitern.
   - Pfade in allen `*.md`-Dateien konsistent anpassen.

---

## **Offene Fragen**
1. **Datenbank-Format:**
   - Soll die Datenbank weiterhin SQLite verwenden oder auf ein anderes Format migriert werden?
2. **Berechtigungen:**
   - Werden spezielle Berechtigungen für das Zielverzeichnis `/home/git/ProjektFitness` benötigt?
3. **CI/CD:**
   - Soll ein automatisierter Build-Prozess (z. B. GitHub Actions) für das neue Repository eingerichtet werden?