# Fortschritt

> Kurzes, verständliches Änderungs-Protokoll dieses Projekts. Neueste Einträge oben.
> Claude Code ergänzt hier nach jedem abgeschlossenen Schritt eine Zeile (Datum + was gemacht wurde).
> Dient als Brücke zu Kis Wissens-Gedächtnis (Obsidian).

## 2026-07-05
- Grundgerüst mit FastAPI-Startseite
- CSV-Upload und Warenkorb-Anzeige
- Direkteingabe von Artikeln/EANs zusätzlich zum CSV-Upload
- Echter Shop-Adapter Elektro-Wandelt (Doofinder-Such-API, Matching per EAN/Herstellernummer)
- EAN-Suche für Elektro-Wandelt zum Laufen gebracht (Doofinder findet EAN + Herstellernummer)
- Zweiter Shop-Adapter elektroland24 (Shopware 6, Suche per EAN/Herstellernummer, Preis/Verfügbarkeit von der Produktseite)
- Neue Vergleichsseite im Wunschdesign: Produkte mit Bild + Mengen-Schaltern, beide Shops nebeneinander, günstigster Shop als „best choice" grün, Summen mit Warenkorb-Link, Mengen live umgerechnet
- „Warenkorb bei Shop"-Button füllt den Shop-Warenkorb mit allen gewählten Artikeln vor (Elektro-Wandelt per Link, elektroland24 per Formular) – ein Klick, kein erneutes Hinzufügen nötig
- Versandkosten in die Rechnung aufgenommen (Elektro-Wandelt 4,90 €, elektroland24 5,90 €): Gesamt = Artikel + Versand, günstigster Shop wird inklusive Versand bestimmt; Summenzeile zeigt Artikel/Versand/Gesamt getrennt
- Versandart-Umschalter (Paket/Sperrgut/Spedition) mit den offiziellen Preisen beider Shops; Gratis-Versand-ab-Funktion eingebaut (aktuell 0, da keine offizielle Grenze belegt); alles live umgerechnet
- Vergleichsseite komplett neu gestaltet: minimalistisches, modernes Design (Inter-Schrift, viel Weißraum, feine Trennlinien, Segmented-Control für die Versandart, „Günstigste Wahl"-Badge, Ersparnis-Chip, dezente Animationen)
- Startseite im gleichen minimalistischen Design überarbeitet: Hero, zwei Karten (CSV-Upload mit Drag&Drop-Feld und Direkteingabe), einheitliche Schrift/Farben, Shop-Chips
- Deployment vorbereitet (Render): feste Paketversionen, render.yaml, Procfile, .python-version, DEPLOY.md-Anleitung – Ziel-Domain macherelektro.de (IONOS)
- LIVE gegangen: App läuft auf Render (Region Frankfurt) und ist unter https://www.macherelektro.de erreichbar (HTTPS aktiv); IONOS-DNS verbunden (A @ → 216.24.57.1, CNAME www → elektrovergleich.onrender.com). End-to-End auf der Live-Domain getestet
- Tempo massiv verbessert: Shops parallel + Artikel je Shop parallel (kleiner Pool) + 10-Minuten-Zwischenspeicher. 4 Artikel: vorher ~6,5 s → jetzt ~1,9 s, wiederholter Vergleich ~0 s; Server bleibt während der Abfragen für andere Besucher ansprechbar
- Dritter Shop Voltus angebunden (OXID/FactFinder): Suche per EAN + Herstellernummer, Preis/Verfügbarkeit, Warenkorb-Link, Versandkosten (Paket 6,90 / Sperrgut 29,90 / Spedition 77,00 €). Drei-Shop-Vergleich im Browser getestet
- Elektroshop Wagner NICHT angebunden: aktiver Bot-Schutz (Akamai, alle Zugriffe 403); saubere Umgehung nicht möglich/gewollt. Legitimer Weg wäre ein offizieller Produktfeed (Affiliate-Netzwerk)
