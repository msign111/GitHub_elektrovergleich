# eingabe.py – Wandelt direkt eingetippten Text in Warenkorb-Positionen um.
# Der Nutzer kann pro Zeile einen Artikel eingeben, z. B.:
#   4012740123456          (nur eine EAN)
#   MBN116                 (nur eine Artikelnummer)
#   4012740123456; 10      (EAN mit Menge 10)
#   MBN116; 5              (Artikelnummer mit Menge 5)

from app.modelle import Position


def _ist_ean(text: str) -> bool:
    """Eine EAN besteht nur aus Ziffern und ist typischerweise 8–14 Stellen lang."""
    return text.isdigit() and len(text) in (8, 12, 13, 14)


def positionen_aus_text(text: str) -> list[Position]:
    """
    Nimmt den getippten Text (mehrere Zeilen) und gibt eine Liste
    von Positionen zurück. Eine Zeile = ein Artikel.
    """
    positionen: list[Position] = []

    for zeile in text.splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue  # Leerzeilen überspringen

        # Zeile in Teile zerlegen: erst der Artikel, optional dahinter die Menge.
        # Erlaubt als Trennzeichen Semikolon, Komma oder Tab.
        teile = [t.strip() for t in zeile.replace("\t", ";").replace(",", ";").split(";")]
        teile = [t for t in teile if t]

        kennung = teile[0]

        # Menge herauslesen, falls angegeben – sonst 1 annehmen.
        menge = 1
        if len(teile) > 1:
            try:
                menge = int(teile[1])
            except ValueError:
                menge = 1

        # Ist die Kennung eine EAN oder eine Artikelnummer?
        if _ist_ean(kennung):
            ean = kennung
            artikelnummer = ""
        else:
            ean = ""
            artikelnummer = kennung

        positionen.append(
            Position(
                hersteller="",
                artikelnummer=artikelnummer,
                ean=ean,
                menge=menge,
                beschreibung="",
            )
        )

    return positionen
