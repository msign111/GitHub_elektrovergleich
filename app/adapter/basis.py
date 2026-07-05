# basis.py – Die gemeinsame Schnittstelle für ALLE Shop-Adapter.
#
# Idee: Jeder Shop wird durch eine eigene Klasse dargestellt, die von
# ShopAdapter erbt und die Methode `angebot_fuer(position)` ausfüllt.
# Der Rest der App spricht nur mit `get_offers(positionen)` und muss
# nichts über den einzelnen Shop wissen. So kommen neue Shops dazu,
# ohne dass der Kern geändert werden muss.

import time

from app.modelle import Position, Angebot


class ShopAdapter:
    """Basisklasse für alle Shop-Adapter."""

    name = "Basis"          # wird in den Unterklassen überschrieben
    website = ""            # Startseite des Shops (für den Warenkorb-Link)
    warenkorb_typ = ""      # "oxid" (Link) oder "shopware" (Formular) – leer = nicht unterstützt
    warenkorb_endpunkt = "" # URL, an die der Warenkorb-Aufruf geht

    # Versandkosten-Pauschalen (Deutschland) je Versandart, in Euro
    versand_paket = 0.0
    versand_sperrgut = 0.0
    versand_spedition = 0.0
    # Gratis-Versand ab diesem Bestellwert (0 = kein Gratis-Versand). Gilt nur für Paketversand.
    versandfrei_ab = 0.0

    def __init__(self, pause: float = 1.0):
        # Pause (in Sekunden) zwischen zwei Anfragen an denselben Shop –
        # damit wir den Shop-Server nicht überlasten.
        self.pause = pause

    def angebot_fuer(self, position: Position) -> Angebot:
        """
        Sucht EIN Angebot für EINE Position.
        Muss von jeder Shop-Klasse selbst umgesetzt werden.
        """
        raise NotImplementedError("Diese Methode muss der jeweilige Shop-Adapter umsetzen.")

    def get_offers(self, positionen: list[Position]) -> list[Angebot]:
        """
        Holt für jede Position ein Angebot. Gibt eine Liste in derselben
        Reihenfolge wie die Positionen zurück. Fehler bei einer Position
        stoppen nicht den ganzen Vorgang.
        """
        angebote: list[Angebot] = []
        for i, position in enumerate(positionen):
            # Vor jeder Anfrage (außer der ersten) kurz warten – höflich zum Shop.
            if i > 0:
                time.sleep(self.pause)
            try:
                angebote.append(self.angebot_fuer(position))
            except Exception as fehler:
                angebote.append(
                    Angebot(shop=self.name, hinweis=f"Fehler beim Abruf: {fehler}")
                )
        return angebote
