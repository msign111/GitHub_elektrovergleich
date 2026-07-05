# SPEC – Vergleichsplattform für Elektromaterial (MVP)

> Briefing für Claude Code. Beschreibt zuerst den kleinen MVP, dann die volle Vision. **Immer zuerst den MVP bauen.**

## Ziel
B2B-Plattform, die komplette Warenkörbe (nicht Einzelprodukte) über mehrere Elektrogroßhändler vergleicht und nach **Preis + Lieferfähigkeit** optimiert. Zielgruppe: Elektroinstallateure, Handwerk, Industrie, Einkauf.

## MVP – das bauen wir zuerst (klein halten!)
1. Nutzer lädt einen Warenkorb als **CSV** hoch.
2. System fragt **2–3 Beispiel-Shops** ab (zunächst Testdaten, keine echten Webseiten).
3. **Matching** der Positionen: zuerst über EAN, Fallback Herstellernummer.
4. **Vergleichsansicht**: pro Shop Gesamtpreis, Anteil lieferbarer Positionen (%), fehlende Artikel; beste Kombination hervorheben.

### Datenmodell – Warenkorb-Position
- Hersteller (Text)
- Artikelnummer (Text)
- EAN (Text, optional)
- Menge (Zahl)
- Beschreibung (Text)

### Shop-Angebot (pro Position und Shop)
- Preis, Verfügbarkeit, Lieferzeit, Versandkosten, Produktlink, Verpackungseinheit, Mindestbestellmenge

## Tech-Stack (einfach & wartbar)
- **Backend:** Python + FastAPI
- **Datenbank:** SQLite (für den MVP, keine Extra-Installation)
- **Frontend:** einfaches, server-gerendertes HTML (später ausbaubar)
- **Datenquellen:** austauschbare **Shop-Adapter** mit gemeinsamer Schnittstelle. MVP = Adapter mit Beispieldaten.

## Architektur (Zielbild)
- Je Shop ein **Adapter** hinter einer gemeinsamen Schnittstelle `get_offers(positions) -> offers`.
- Ein **Orchestrator** ruft alle Adapter (später parallel) auf und führt die Ergebnisse zusammen.
- **Matching-Modul** ordnet Positionen den Angeboten zu (EAN, dann Herstellernummer).
- **Vergleichs-/Scoring-Modul** berechnet Gesamtpreis, Lieferfähigkeit und eine Empfehlung.
- Neue Shops sollen **ohne Änderung am Kern** ergänzbar sein.

## Wichtige Regeln
- Der Nutzer ist **kein Programmierer** – erkläre jeden Schritt einfach; nenne immer den genauen Befehl zum Starten/Testen.
- **Kleine Schritte**, nach jedem Schritt lauffähig halten und per Git sichern.
- **Kein Scraping echter fremder Shops** im MVP. Nur Beispiel-/Testdaten. Echte Preisdaten später ausschließlich über erlaubte Quellen (offizielle APIs, Produkt-Feeds, Kooperationen); AGB beachten.
- **Keine Geheimnisse** (Passwörter, Keys) im Code – später über Umgebungsvariablen.

## Später (nach dem MVP, nicht jetzt)
Benutzerkonten & Login; Warenkorbverwaltung (speichern/kopieren/archivieren); weitere Importe (Excel, GAEB, IDS, OCI, SAP); Preisverlauf (30/90/365 Tage) & Preisalarme; Produktdetailseiten; intelligenter Score; Admin-Backend (Monitoring, Mappings, Shops verwalten); echte Shop-Anbindungen; KI-Alternativvorschläge; Mobile App / Browser-Erweiterung.
