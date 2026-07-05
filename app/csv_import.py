# csv_import.py – Liest eine hochgeladene CSV-Datei ein
# und macht daraus eine Liste von Warenkorb-Positionen.

import csv
import io

from app.modelle import Position


# Mögliche Spaltennamen in der CSV -> unser einheitlicher Name.
# So darf die CSV z. B. "Menge", "Anzahl" oder "Stück" heißen.
SPALTEN_ALIASE = {
    "hersteller": "hersteller",
    "marke": "hersteller",
    "artikelnummer": "artikelnummer",
    "artikel-nr": "artikelnummer",
    "artikelnr": "artikelnummer",
    "herstellernummer": "artikelnummer",
    "ean": "ean",
    "gtin": "ean",
    "menge": "menge",
    "anzahl": "menge",
    "stück": "menge",
    "stueck": "menge",
    "beschreibung": "beschreibung",
    "bezeichnung": "beschreibung",
    "text": "beschreibung",
}


def _spalte_zuordnen(spaltenname: str) -> str | None:
    """Wandelt einen CSV-Spaltennamen in unseren einheitlichen Namen um."""
    sauber = spaltenname.strip().lower()
    return SPALTEN_ALIASE.get(sauber)


def csv_einlesen(dateiinhalt: bytes) -> list[Position]:
    """
    Nimmt den Inhalt einer CSV-Datei (als Bytes) und gibt eine Liste
    von Positionen zurück. Erkennt automatisch, ob Semikolon oder
    Komma als Trennzeichen benutzt wird (in Deutschland oft Semikolon).
    """
    # Bytes in Text umwandeln. utf-8-sig entfernt ein evtl. vorhandenes
    # unsichtbares Sonderzeichen am Dateianfang (BOM), das Excel manchmal setzt.
    text = dateiinhalt.decode("utf-8-sig")

    # Trennzeichen automatisch erkennen (Semikolon, Komma oder Tab).
    try:
        dialekt = csv.Sniffer().sniff(text[:1024], delimiters=";,\t")
    except csv.Error:
        # Falls die Erkennung scheitert: Semikolon als Standard annehmen.
        dialekt = csv.excel
        dialekt.delimiter = ";"

    leser = csv.DictReader(io.StringIO(text), dialect=dialekt)

    # Zuordnung: welche CSV-Spalte gehört zu welchem unserer Felder?
    zuordnung = {}
    for csv_spalte in leser.fieldnames or []:
        ziel = _spalte_zuordnen(csv_spalte)
        if ziel:
            zuordnung[ziel] = csv_spalte

    positionen: list[Position] = []
    for zeile in leser:
        # Werte anhand der Zuordnung herausholen (leer, falls Spalte fehlt).
        def hole(feld: str) -> str:
            csv_spalte = zuordnung.get(feld)
            wert = zeile.get(csv_spalte, "") if csv_spalte else ""
            return (wert or "").strip()

        # Menge in eine Zahl umwandeln; bei Fehler 0 annehmen.
        try:
            menge = int(hole("menge"))
        except ValueError:
            menge = 0

        # Leere Zeilen (ohne Artikelnummer und ohne EAN) überspringen.
        if not hole("artikelnummer") and not hole("ean"):
            continue

        positionen.append(
            Position(
                hersteller=hole("hersteller"),
                artikelnummer=hole("artikelnummer"),
                ean=hole("ean"),
                menge=menge,
                beschreibung=hole("beschreibung"),
            )
        )

    return positionen
