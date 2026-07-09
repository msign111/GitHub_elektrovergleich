# Fortschritt

> Kurzes, verständliches Änderungs-Protokoll dieses Projekts. Neueste Einträge oben.
> Claude Code ergänzt hier nach jedem abgeschlossenen Schritt eine Zeile (Datum + was gemacht wurde).
> Dient als Brücke zu Kis Wissens-Gedächtnis (Obsidian).

## 2026-07-09
- Wagner-Sammel-Warenkorb doch möglich! Die „Warenkorb aktualisieren"-Funktion des Shops (`/de/cart?action=update_product` mit `products_id[]`/`cart_quantity[]`) legt in EINEM Aufruf mehrere Artikel samt Mengen auch NEU an (live mit leerem Warenkorb getestet, inkl. korrekter Varianten). Wagner hat jetzt denselben „Zum Warenkorb"-Knopf wie die anderen Shops (neuer Typ „gambio"); die Einzel-Artikel-Knöpfe samt Klick-Bremse wurden wieder entfernt.
- Wagner-Varianten repariert: Bei Varianten-Artikeln (z. B. Hager MBN106–163) landete die falsche Variante im Warenkorb (immer die erste der Liste). Jetzt wird die Position der gesuchten EAN/Herstellernummer in Wagners Varianten-Listen ermittelt und die richtige Produkt-ID verwendet (Warenkorb + Produktlink). Zusätzlich ehrliche Preis-Regel: Wagners Suche liefert nur den Preis der Basis-Variante – für andere Varianten (Preise weichen ab, z. B. MBN116 2,79 € vs. MBN106 7,24 €) zeigen wir statt eines falschen Preises „Preis nur im Shop" mit Link zur richtigen Variante.
- Wagner-Warenkorb-Knöpfe: Klick-Bremse (4 s Sperre nach jedem Klick) und fester Ziel-Tab, damit schnell hintereinander geklickte Artikel nicht in getrennten Warenkörben landen.
- Wagner-Warenkorb: Der Shop (Gambio) kann nur EINEN Artikel pro Aufruf aufnehmen (kein Sammel-Warenkorb wie OXID/Shopware, getestet). Deshalb neuer Warenkorb-Typ „einzeln": In der Wagner-Spalte hat jetzt jeder Artikel einen eigenen „In den Warenkorb"-Knopf (öffnet Wagner im neuen Tab mit genau diesem Artikel + Menge). Footer bleibt „Zum Shop".
- Vierter Shop angebunden: **Elektroshop Wagner** (`app/adapter/wagner.py`). Preise/Verfügbarkeit/Produktlinks kommen über die offene Algolia-Suche des Shops (die Shop-Seiten selbst blocken automatisierte Zugriffe). Kein Warenkorb-Vorbefüllen möglich – dafür zeigt die Vergleichsseite bei solchen Shops jetzt „Zum Shop". Versand: Paket 4,95 €, Spedition ab 39,95 €. Live getestet: Vergleich mit 4 Shops funktioniert, Wagner war im Test die günstigste Wahl.

## 2026-07-08
- Marken-Monitor (täglicher Crawler + Dashboard) in ein eigenes, getrenntes Projekt ausgelagert: `C:\Dev\wandelt-marken-monitor` (Crawling über n8n-Cloud, Daten in Google-Tabelle, Dashboard als HTML-Datei). Die zuerst hier eingebauten Reste (`crawler_topartikel.py`, Seite `/dashboard`) wurden wieder entfernt, damit dieses Projekt nur die reine Preisvergleich-App bleibt.
- Oraya-Auswertung aktualisiert: aktuelle Verkaufszahlen aller 214 Artikel bei Elektro-Wandelt abgefragt (Doofinder-Feld „verkaufsrang" = „wurde bereits X mal gekauft") und neue Excel mit Markenvergleich + Platzierungs-Diagramm erstellt (Downloads\Oraya Auswertung Update 08.07.2026.xlsx). Ergebnis: Merten wächst mit +50 % seit Feb. 2024 am stärksten.

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
- Neuer „Entdecken"-Bereich zum Stöbern: eigener, neutraler Kategoriebaum + Live-Suche mit Vorschlägen (Autocomplete); Produkte per Klick in die Auswahl legen und mit einem Klick vergleichen. Bewusst KEINE Kopie eines fremden Katalogs – alles on-demand/live
- Direkteingabe (Variante 2) interaktiv gemacht: Artikelnummer/EAN einzeln eingeben → Bild, Name und Richtpreis werden angezeigt, Menge pro Artikel wählbar; die Liste geht per „Vergleich starten" in den Preisvergleich
- Startseite neu geordnet: interaktive Artikel-Erfassung steht oben im Fokus, CSV-Upload darunter als Alternative; „Variante"-Beschriftungen entfernt
- Startseite im Design überarbeitet (angelehnt an aktuelle Trends): große Typografie, dezente Hintergrund-Farbverläufe (Tiefe), dominante „schwebende" Hauptkarte mit Eyebrow-Label; CSV-Upload klein/kompakt als Alternative; mobil gestapelt
- Autovervollständigung im Erfassungsfeld: Vorschläge (Bild, Name, Preis) beim Tippen von Marke/Bezeichnung/EAN/Artikelnummer, nach Relevanz/Verkaufsrang sortiert; Klick übernimmt den Artikel mit präziser Artikelnummer/EAN
- Passwortschutz für die ganze Seite (Login-Seite + Cookie); Passwort „elektrohase", überschreibbar per Umgebungsvariable SEITEN_PASSWORT
- Frischer Stil (Hintergrund-Verläufe, größere Überschrift) auch auf die Vergleichsseite angewendet
- Warenkorb-Fix für OXID-Shops (Wandelt, Voltus): „Zum Warenkorb" ist jetzt ein echter Link statt window.open – so blockiert kein Popup-Blocker mehr den Aufruf (v. a. beim zweiten Klick). Link-Adresse aktualisiert sich mit der Menge; elektroland24 bleibt beim Formular (POST)
