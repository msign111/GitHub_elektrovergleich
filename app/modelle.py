# modelle.py – Beschreibt die Datenstrukturen der App.
# Hier legen wir fest, wie eine Warenkorb-Position und ein Shop-Angebot aussehen.

from dataclasses import dataclass


@dataclass
class Position:
    """Eine einzelne Zeile aus dem Warenkorb (ein Artikel)."""

    hersteller: str          # z. B. "Hager"
    artikelnummer: str       # Herstellernummer, z. B. "MBN116"
    ean: str                 # Strichcode-Nummer (optional, kann leer sein)
    menge: int               # Wie viele Stück
    beschreibung: str        # Klartext, z. B. "Leitungsschutzschalter B16"


@dataclass
class Angebot:
    """Das Ergebnis eines Shops für eine Warenkorb-Position."""

    shop: str                        # Name des Shops, z. B. "Elektro-Wandelt"
    gefunden: bool = False           # Wurde der Artikel im Shop gefunden?
    preis: float | None = None       # Einzelpreis brutto in Euro (Zahl zum Rechnen)
    preis_text: str = ""             # Originaltext, z. B. "3,05 €"
    verfuegbarkeit: str = ""         # z. B. "auf Lager"
    lieferbar: bool = False          # Ist der Artikel lieferbar?
    titel: str = ""                  # Produkttitel im Shop
    produktlink: str = ""            # Direktlink zum Produkt im Shop
    bild: str = ""                   # Bild-URL des Produkts (für die Anzeige)
    shop_produkt_id: str = ""        # interne Produkt-ID im Shop (für den Warenkorb-Link)
    hinweis: str = ""                # z. B. "Kein Treffer" oder eine Fehlermeldung

    def gesamtpreis(self, menge: int) -> float | None:
        """Preis für die gewünschte Menge (Einzelpreis × Menge)."""
        if self.preis is None:
            return None
        return round(self.preis * menge, 2)
