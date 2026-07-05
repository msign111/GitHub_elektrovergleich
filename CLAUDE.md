# Projektkontext für Claude Code

Projekt: **„Vergleichsplattform für Elektromaterial"**. Der vollständige Plan steht in `SPEC.md` – bitte zuerst lesen.

## Wichtig über den Nutzer
- Der Nutzer (Ki) ist **kein Programmierer**.
- Erkläre alles in **einfacher, deutscher Sprache**.
- Nach jedem Schritt: nenne **genau den Befehl**, den er eingeben muss, um die App lokal im Browser zu testen.
- Arbeite in **kleinen, nachvollziehbaren Schritten** – nicht viele Features auf einmal.

## Technische Konventionen
- Stack: **Python + FastAPI + SQLite + einfaches HTML**.
- Code sinnvoll **auf Deutsch kommentieren**.
- Modular bleiben: **Shop-Adapter** hinter gemeinsamer Schnittstelle, damit neue Shops ohne Kernänderung dazukommen.
- **Kein automatisiertes Abfragen echter fremder Shops.** Im MVP nur Beispiel-/Testdaten. Echte Datenquellen später ausschließlich über offizielle APIs/erlaubte Feeds; AGB beachten.
- **Keine Passwörter/API-Keys** im Code – Umgebungsvariablen verwenden.

## Arbeitsweise
- Baue zuerst den **MVP** aus `SPEC.md` (CSV-Import → 2–3 Beispiel-Shops → EAN-Matching → Vergleichstabelle).
- Halte die App nach **jedem Schritt lauffähig**.
- **Git:** nach jedem funktionierenden Schritt committen, damit nichts verloren geht.
- Bevor du viel Code änderst: **kurz erklären, was und warum**, dann umsetzen.

## Fortschritt festhalten
- Nach **jedem abgeschlossenen Schritt** eine kurze, verständliche Zeile oben in `FORTSCHRITT.md` ergänzen (Datum + was gemacht wurde). Das ist die Brücke zu Kis Wissens-Gedächtnis in Obsidian.
